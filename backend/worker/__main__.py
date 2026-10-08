"""Explicit local worker commands; importing/running tests never starts a daemon."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from backend.assistant.gateway import DomainGateway
from backend.assistant.mcp_gateway import McpGateway
from backend.assistant.providers import AssistantError
from backend.assistant.runner import parse_decision
from backend.worker.engine import run_once
from backend.worker.queue import Queue


async def action(args, queue):
    base=os.environ.get('API_URL','http://127.0.0.1:8020').rstrip('/')
    DomainGateway(base,'validate-before-login')
    username,password=os.environ.get('WORKER_USERNAME'),os.environ.get('WORKER_PASSWORD')
    tenant=os.environ.get('WORKER_TENANT_ID')
    if not username or not password or not tenant:
        raise AssistantError('worker_identity_configuration_required')
    try:
        tenant=str(UUID(tenant))
    except ValueError:
        raise AssistantError('invalid_worker_tenant') from None
    async with httpx.AsyncClient(base_url=base,trust_env=False,follow_redirects=False,timeout=10) as client:
        response=await client.post('/auth/login',json={'username':username,'password':password})
        if response.status_code!=200:
            raise AssistantError('worker_login_failed')
        token=response.json()['access_token']
        gateway=DomainGateway(base,token)
        try:
            identity=await gateway.authenticate()
            if identity['tenant_id']!=tenant:
                raise AssistantError('worker_tenant_mismatch')
            if args.command in {'enqueue','schedule'}:
                path=Path(args.request_file)
                if path.stat().st_size>16384:
                    raise AssistantError('invalid_job')
                decision=parse_decision(path.read_text(encoding='utf-8'))
                if args.command=='enqueue':
                    result={'job_id':queue.enqueue(identity,args.event_key,decision)}
                else:
                    queue.add_schedule(identity,args.name,args.interval,decision)
                    result={'schedule_id':args.name,'state':'enabled'}
            elif args.command=='disable-schedule':
                queue.disable_schedule(identity,args.name)
                result={'schedule_id':args.name,'state':'disabled'}
            elif args.command=='inspect':
                result=queue.inspect(identity,args.job_id)
            else:
                transport=os.environ.get('WORKER_TRANSPORT','mcp')
                if transport=='mcp':
                    async with McpGateway(base,token) as mcp:
                        result=await run_once(queue,mcp)
                elif transport=='http':
                    result=await run_once(queue,gateway)
                else:
                    raise AssistantError('invalid_worker_transport')
            print(json.dumps(result,ensure_ascii=True))
        finally:
            await client.post('/auth/logout',headers={'Authorization':'Bearer '+token})


async def main(args):
    if args.env_file:
        load_dotenv(args.env_file,override=False)
    queue=Queue(args.queue)
    count=args.max_ticks if args.command=='run' else 1
    if not 1<=count<=1000 or not 1<=args.poll_seconds<=3600:
        raise AssistantError('invalid_worker_limits')
    for tick in range(count):
        await action(args,queue)
        if tick+1<count:
            await asyncio.sleep(args.poll_seconds)


def cli():
    parser=argparse.ArgumentParser(description='Scoped local automation worker; read/prepare/reconcile only.')
    parser.add_argument('--env-file')
    parser.add_argument('--queue',default='local/worker/jobs.sqlite3')
    parser.add_argument('--max-ticks',type=int,default=12)
    parser.add_argument('--poll-seconds',type=int,default=5)
    commands=parser.add_subparsers(dest='command',required=True)
    enqueue=commands.add_parser('enqueue');enqueue.add_argument('event_key');enqueue.add_argument('request_file')
    schedule=commands.add_parser('schedule');schedule.add_argument('name');schedule.add_argument('interval',type=int);schedule.add_argument('request_file')
    disable=commands.add_parser('disable-schedule');disable.add_argument('name')
    inspect=commands.add_parser('inspect');inspect.add_argument('job_id')
    commands.add_parser('run-once');commands.add_parser('run')
    try:
        asyncio.run(main(parser.parse_args()))
    except AssistantError as exc:
        parser.exit(1,str(exc)+'\n')
    except (httpx.HTTPError,ValueError,KeyError,TypeError,ValidationError,OSError,sqlite3.Error):
        parser.exit(1,'worker_unavailable_or_invalid_configuration\n')
    except KeyboardInterrupt:
        parser.exit(130,'worker_cancelled\n')


if __name__=='__main__':
    cli()

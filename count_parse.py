#!/usr/bin/env python
import os, sys, re, time
from plumbum import local, cli, FG, BG, TF, TEE, ProcessExecutionError, colors
from plumbum.cmd import echo
from contextlib import contextmanager
from tinydb import TinyDB, Query, where
import pendulum
from loguru import logger
from mako.template import Template

class MyApp(cli.Application):
    def main(self, db : cli.ExistingFile, block : cli.ExistingFile, out_html : cli.NonexistentPath, validators_elected_for = 65536 ):
        try:
            with open(block, 'r') as infile:
                data = infile.read()
            blocks = data.splitlines()
            template = Template(filename='template.txt')

            db = TinyDB(db)
        except Exception as error:
            logger.opt(exception=True).debug('Failed on open files')                    

        query = Query()
        start = 0   # set to another number if you want to skip some records from start 
        query_res = db.search(((query['success'] == True) | (query['reward'] != -1)) & (query['id'] >= start))
        work=[]
        t = 0
        count=0
        count_reward = 0
        try:
            for i in range(len(query_res)):
                if (query_res[i]['success'] == True ):
                    count+=1
                    #print(count,query_res[i])
                    t=i
                    while (t+1 < len(query_res)):
                        t+=1
                        if (query_res[t]['reward'] != -1):
                            if ( (query_res[t]['time'] - query_res[i]['election_time']) < (int(validators_elected_for) + 500) ): # empirically found value, when 'validators_elected_for' was 4000 = 4500 
                                continue
                            z = {'id_reward': query_res[t]['id'], 'election_time': query_res[i]['election_time'], 'reward_time': query_res[t]['time'], 'reward': query_res[t]['reward'] , 'blocks': 0}
                            work.append(z)
                            count_reward+=1
                            #print(count_reward, z)
                            break
        except Exception as error:
            logger.opt(exception=True).debug('Failed on binding')                    
        
        # cat db.json | jq -r '._default' | jq '[.[]]' | grep "reward" |  grep  -v '"reward": -1,' | awk 'BEGIN{FS=":"} {print ($2/1000000000) }''| wc -l
        logger.info("Count of parsed reward records = {}, success records = {}, please check it with cat | grep", count_reward, count)

        try:
            for i in range(len(work)):
                if (i+1 < len(work)):    
                    #print(i,work[i])
                    if ((work[i]['reward'] == work[i+1]['reward'])):
                        logger.info("Duplicates found, deleting first occurence")
                        #print(i,work[i])
                        del(work[i])
        except Exception as error:
            logger.opt(exception=True).debug('Failed on deleting duplicates')                    

        try:
            for i in range(len(work)):
                a = work[i]['election_time']
                b = a + int(validators_elected_for)
                sum = 0
                for y in blocks:
                    d = int(y)
                    if (d >= a  and d <= b):
                        sum+=1                
                if (sum != 0) :
                    work[i]['blocks'] = sum
                    #print(work[i]['blocks'])

            print("------------------------------------")
            for i in range(len(work)):
                print(work[i]) # Resulting array
            print("------------------------------------")
            text=[]
            sep=","
            for i in range(len(work)):
                #if ((work[i]['blocks'] != 0)): # Maybe you can get rewards without validating any blocks
                    dt = pendulum.from_timestamp(work[i]['election_time'])
                    pr=dt.format('YYYY,MM,DD HH:mm:ss')
                    #pr=dt.to_datetime_string()
                    #pr=dt.to_iso8601_string()
                    #print(f"[new Date(\"{pr}\"), {work[i]['reward'] / 1000000000}, \"{work[i]['election_time']}\", {work[i]['blocks']}]")
                    text.append(f"[new Date(\"{pr}\"), {work[i]['reward'] / 1000000000}, \"{work[i]['election_time']}\", {work[i]['blocks']}]")
            FilledTemplate = template.render(Variable=(sep.join( text )))
            FileName = out_html
            f= open(FileName,"w+")
            f.write(FilledTemplate)
            f.close()

        except Exception as error:
            logger.opt(exception=True).debug('Failed on last iter')                    

if __name__ == "__main__":
    MyApp.run()
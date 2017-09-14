#!/bin/env/python

import base

class Runshell(base.Utils):

    # init parent class with region
    def __init__(self, region):
        base.Utils.__init__(self, region)

    # To run shell commands on ec2 instance
    def run_shell_cmd(self, instance_ids, command, comment):
        response = self.ssm.send_command(
            InstanceIds = instance_ids,
            DocumentName = 'AWS-RunShellScript',
            TimeoutSeconds = 30,
            Comment=comment,
            Parameters = {
                'commands': [
                    command,
                ]
            }
        )
        return response

    # check if command job finished
    def job_status(self, instance_ids, job_id):
        instances = []
        passed = 0
        while True:
            if len(instances) == len(instance_ids):
                break
            for instance in instance_ids:
                if instance not in instances:

                    get_status = self.ssm.list_commands(CommandId = job_id, InstanceId = instance)
                    status = get_status['Commands'][0]['Status']

                    if status == 'Success':
                        print "%s : cmd success!" %(instance)
                        passed = passed + 1
                        instances.append(instance)
                    if status == 'TimedOut' or status == 'Failed' or status == 'Cancelled':
                        print "%s : cmd failed" %(instance)
                        instances.append(instance)

        if passed != len(instance_ids):
            return False
        return True

    # do it
    def run_command(self, instance_ids, cmd):
        print "Executing command: %s" % cmd
        command = self.run_shell_cmd(instance_ids, cmd, cmd)
        return self.job_status(instance_ids, command['Command']['CommandId'])

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3

from aws_cdk import core

from cdk.vpc_base.vpc import CdkVpcStack
from cdk.pipeline.pipeline import CdkPipelineStack
from cdk.pipeline.hostpipeline import CdkPipelinedeployStack
from cdk.pipeline.codedeploy import Codedeployec2
#from cdk.pipeline.hostpipelinecdk import CdkPipelinedeployStackhost1

class AwsEnvParity(core.App):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

            self.stack_name = "app"
            self.base_module = CdkVpcStack(self, self.stack_name + "-base")
            self.pipeline_module = CdkPipelineStack(self, self.stack_name + "-pipeline", self.base_module.vpc)
            self.pipelinedeploy_module = CdkPipelinedeployStack(self, self.stack_name + "-deploypipeline", self.base_module.vpc)
            self.pipelinedeployhost_module = Codedeployec2(self, self.stack_name + "-pipelinedeploy-ec2", self.base_module.vpc)
 #           self.pipelinedeployhost_module = CdkPipelinedeployStackhost1(self, self.stack_name + "-deploypipelinehost", self.base_module.vpc)

if __name__ == '__main__':
    app = AwsEnvParity()
    app.synth()

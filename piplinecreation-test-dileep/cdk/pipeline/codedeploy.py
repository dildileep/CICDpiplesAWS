from aws_cdk import core
import aws_cdk.core
#import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
#import aws_cdk.aws_iam as iam
import aws_cdk.aws_codecommit as codecommit

import aws_cdk.aws_codedeploy as codedeploy
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import os

from aws_cdk import (core,aws_ec2 as ec2,aws_iam as iam)


import aws_cdk.aws_codecommit as code_commit

class Codedeployec2(core.Stack):
    
    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        name = "code-deploy-pipeline"
#        vpcId = vpc
        instanceName = f"{name}-ec2"
        instanceType = "t2.micro"
        amiName = "amzn2-ami-hvm-2.0.20200520.1-x86_64-gp2"
        keyPair = "key_dil"

        # pull the values from the props dictionary
        #roleArn = props["ec2role"]

        # get the aws environment details
        #env = kwargs['env']
        
        userData = "sudo yum -y update; sudo yum install -y ruby aws-cli wget ; \
        cd /home/ec2-user; wget https://aws-codedeploy-ap-south-1.s3.amazonaws.com/latest/install ; \
        sudo chmod +x ./install; sudo ./install auto ; sudo service codedeploy-agent status"
        
        vpc1 = ec2.Vpc(self, "VPC",
            nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(name="public",subnet_type=ec2.SubnetType.PUBLIC)]
            )
        
        # = ecr.Repository(scope=self,id=f"{name}-container",repository_name=f"{name}")
        
        container_repository = code_commit.Repository(self, "CodeCommitRepository",repository_name=f"{name}Repo")
        
        # create a security group
        sec_group = ec2.SecurityGroup(self, "sec-group",security_group_name=f"{name}-sg", vpc=vpc1, allow_all_outbound=True)
        # add ingress rule for ssh
        sec_group.add_ingress_rule(peer=ec2.Peer.any_ipv4(),description="Allow SSH connection",connection=ec2.Port.tcp(22),)
        
        # add ingress rule to allow HTTP connections,
        sec_group.add_ingress_rule(peer=ec2.Peer.any_ipv4(),description="Allow HTTP connection",connection=ec2.Port.tcp(80))
        
        
        ec2role = iam.Role(self, "Role", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        ec2role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess"))
        
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )  

        ec2_instance  = ec2.Instance(self, "ec2-instance",
            instance_type=ec2.InstanceType(instanceType),
            machine_image=amzn_linux,
            instance_name=instanceName,
            vpc = vpc1,
            role = ec2role,
            security_group=sec_group,
            key_name=keyPair,
            )
        # attach the custom user data
        ec2_instance.add_user_data(userData)
        
        # add a tag
        core.Tag.add(self, key="Name", value=instanceName)

        
        serverApplication = codedeploy.ServerApplication(self, "MyDemoApplication", application_name="MyDemoApplication")
        
        CodeDeployRole = iam.Role(self, "CodeDeployRole",role_name="CodeDeployRole", assumed_by=iam.ServicePrincipal("codedeploy"))
        
        CodeDeployRole.add_managed_policy(iam.ManagedPolicy.from_managed_policy_arn(self, "managedpolicy", managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"))
        
        
        deployment_group = codedeploy.ServerDeploymentGroup(self, "CodeDeployDeploymentGroup",
            application=serverApplication,
            deployment_group_name="MyDeploymentGroup",
            role=CodeDeployRole,
            # adds User Data that installs the CodeDeploy agent on your auto-scaling groups hosts
            # default: true
            install_agent=True,
            ec2_instance_tags=codedeploy.InstanceTagSet(
            # any instance with tags satisfying
            # key1=v1 or key1=v2 or key2 (any value) or value v3 (any key)
            # will match this group
                {"Name": [instanceName],},
                ),
            )

        
        source_output = codepipeline.Artifact()
        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{name}",
            pipeline_name=f"{name}"
        )
        source_stage = pipeline.add_stage(stage_name="Source")
        deploy_stage = pipeline.add_stage(stage_name="Deploy-toec2")
        
        #source_output = codepipeline.Artifact(artifact_name='source')
        
        source_stage.add_action(
            codepipeline_actions.CodeCommitSourceAction(
                action_name="Source",
                repository=code_commit.Repository.from_repository_name(self,"code_repo",repository_name=f"{name}Repo"),
                run_order=1,
                output=source_output,
                )
            )

        deploy_stage.add_action(
            codepipeline_actions.CodeDeployServerDeployAction(
                deployment_group=codedeploy.ServerDeploymentGroup.from_server_deployment_group_attributes(
                    self,"server_code_deploy_group",
                    application=codedeploy.ServerApplication.from_server_application_name(self,"server_app",server_application_name="MyDemoApplication"),
                    deployment_group_name="MyDeploymentGroup",
                    ),
                action_name="Deploy",
                input=source_output
                )
            )
        
        
        
        core.CfnOutput(
            scope=self,
            id="application_repository",
            value=container_repository.repository_clone_url_http
        )
        
        
        
        
        

        
        
        
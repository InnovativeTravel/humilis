#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import os

import boto3
from boto3facade.cloudformation import Cloudformation
from boto3facade.dynamodb import Dynamodb
from boto3facade.kms import Kms
import yaml

from humilis.config import config
from humilis.exceptions import FileFormatError, RequiresVaultError
from humilis.layer import Layer
import humilis.utils as utils


class Environment():
    """Manages the deployment of a collection of humilis layers."""
    def __init__(self, yml_path, logger=None, stage=None, vault_layer=None):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.__yml_path = yml_path
        self.name = os.path.splitext(os.path.split(yml_path)[1])[0]
        self.stage = stage and stage.upper()
        self.basedir = os.path.split(yml_path)[0]
        with open(yml_path, 'r') as f:
            self.meta = yaml.load(f).get(self.name)

        if len(self.meta) == 0:
            raise FileFormatError(yml_path, logger=self.logger)

        self.cf = Cloudformation(config.boto_config)
        self.sns_topic_arn = self.meta.get('sns-topic-arn', [])
        self.tags = self.meta.get('tags', {})
        self.tags['humilis:environment'] = self.name

        self.layers = []
        for layer in self.meta.get('layers', []):
            layer_name = layer.get('layer', None)
            if layer_name is None:
                msg = "Wrongly formatted layer: {}".format(layer)
                raise FileFormatError(yml_path, msg)
            if layer.get('disable', False):
                message = ("Layer {} is disabled by configuration. "
                           "Skipping.".format(layer.get('layer')))
                self.logger.warning(message)
                continue

            # Get the layer params provided in the environment spec
            layer_params = {k: v for k, v in layer.items() if k != 'layer'}
            layer_obj = Layer(self, layer_name, **layer_params)
            self.layers.append(layer_obj)

        self.vault_layer = self.get_layer(vault_layer or 'secrets-vault')
        self.__secrets_table_name = "secrets_{}_{}".format(self.name,
                                                           self.stage)

    @property
    def outputs(self):
        """Outputs produced by each environment layer"""
        outputs = {}
        for layer in self.layers:
            ly = layer.outputs
            if ly is not None:
                outputs[layer.name] = ly
        return outputs

    @property
    def kms_key_id(self):
        """The ID of the KMS Key associated to the environment vault."""
        if not self.vault_layer:
            raise RequiresVaultError()
        if self.vault_layer:
            return self.outputs[self.vault_layer.name]['KmsKeyId']

    def set_secret(self, key, plaintext):
        """Sets and environment secret."""
        if not self.vault_layer:
            raise RequiresVaultError()
        client = Kms(config.boto_config).client
        encrypted = client.encrypt(KeyId=self.kms_key_id,
                                   Plaintext=plaintext)['CiphertextBlob']
        client = boto3.client('dynamodb')
        resp = client.put_item(
            TableName=self.__secrets_table_name,
            Item={'id': {'S': key}, 'value': {'B': encrypted}})
        return resp

    def get_secret(self, key):
        """Retrieves a secret."""
        if not self.vault_layer:
            raise RequiresVaultError()
        client = Dynamodb(config.boto_config).client
        encrypted = client.get_item(
            TableName=self.__secrets_table_name,
            Key={'id': {'S': key}})['Item']['value']['B']

        # Decrypt using KMS (assuming the secret value is a string)
        client = boto3.client('kms')
        plaintext = client.decrypt(CiphertextBlob=encrypted)['Plaintext']
        return plaintext.decode()

    def create(self, output_file=None, update=False):
        """Creates or updates an environment."""
        self.populate_hierarchy()
        for layer in self.layers:
            layer.create(update=update)
        self.logger.info({"outputs": self.outputs})
        if output_file is not None:
            self.write_outputs(output_file)

    def write_outputs(self, output_file=None):
        """Writes layer outputs to a YAML file."""
        if output_file is None:
            if self.stage is not None and len(self.stage) > 0:
                suffix = "-" + self.stage
            output_file = "{}{}.outputs.yaml".format(self.name, suffix)
        with open(output_file, 'w') as f:
            f.write(yaml.dump(self.outputs, indent=4,
                              default_flow_style=False))

    def populate_hierarchy(self):
        """Adds tags to env layers indicating parent-child dependencies."""
        for layer in self.layers:
            if layer.depends_on and len(layer.depends_on) > 0:
                for parent_name in layer.depends_on:
                    layer = self.get_layer(parent_name).add_child(layer)

    def get_layer(self, layer_name):
        """Gets a layer by name"""
        sel_layer = [layer for layer in self.layers
                     if layer.cf_name == layer_name or
                     layer.name == layer_name]
        if len(sel_layer) > 0:
            return sel_layer[0]

    def delete(self):
        """Deletes the complete environment from CF."""
        for layer in reversed(self.layers):
            layer.delete()

    @property
    def in_cf(self):
        """Returns true if the environment has been deployed to CF."""
        return self.name in {
            utils.unroll_tags(stk['Tags']).get('humilis:environment')
            for stk in self.cf.stacks}

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "Environment('{}')".format(self.__yml_path)

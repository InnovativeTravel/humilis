humilis
==========

[![Circle CI](https://circleci.com/gh/InnovativeTravel/humilis.svg?style=svg)](https://circleci.com/gh/InnovativeTravel/humilis)
[![PyPI](https://img.shields.io/pypi/v/humilis.svg?style=flat)](https://pypi.python.org/pypi/humilis)

Helps you deploy AWS infrastructure with [Cloudformation][cf].

[cf]: https://aws.amazon.com/cloudformation/

This project is originally based on the
[cumulus](https://github.com/germangh/cumulus/blob/master/cumulus/__init__.py).
project. See [CUMULUS_LICENSE][cumulus_license] for license information.

[cumulus]: https://github.com/cotdsa/cumulus
[cumulus_license]: https://github.com/germangh/humilis/blob/master/CUMULUS_LICENSE


# Installation

To install the latest "stable" version:

```
pip install humilis
```

To install the development version:

````
pip install git+https://github.com/germangh/humilis
````


# Development environment

Assuming you have [virtualenv][venv] installed:

[venv]: https://virtualenv.readthedocs.org/en/latest/

```
make develop

. .env/bin/activate
```


# Testing

You will need to first [set up your system][aws-setup] to access AWS resources.

[aws-setup]: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

```
py.test tests
```


# Quickstart

Define your infrastructure environment following the examples in the 
[examples directory][examples-dir]. Then to create the environment:

[examples-dir]: https://github.com/germangh/humilis/tree/master/examples


````
humilis create example-environment.yml
````


And to delete it:

````
humilis delete example-environment.yml
````

For now you can't use humilis to update existing environments.


# Humilis environments

A `humilis` environment is just a collection of cloudformation stacks that
are required for an application. Instead of having a monolytic CF template for
your complete application, `humilis` allows you to define infrastructure
_layers_ that are combined into an _environment_. Each `humilis` layer 
translates exactly into one CF template (therefore into one CF stack after
the layer is deployed).

Breaking a complex infrastructure environment into smaller layers has at least
two obvious advantages:

* __Easier to maintain__. It's easier to maintain a simple layer that contains
  just a bunch of [CF resources][cf-resource] than serve a well-defined
  purpose.

* __Easier to reuse__. You should strive to define your infrastructure
  layers in such a way that you can reuse them across various environments. For
  instance, many projects may require a base layer that defines a VPC, a few
  subnets, a gateway and some routing tables, and maybe a (managed) NAT. You
  can define a humilis layer with those resources and have a set of layer
  parameters (e.g. the VPC CIDR) that will allow you to easily reuse it across
  environments.

[cf-resource]: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html


## Environment anatomy

An environment _definition file_ is a [yaml][yaml] document that specifies the
list of layers that form your enviroment. The file should be named as your 
environment. That is, for environment `my-app-environment` the environment 
description file should be called `my-app-environment.yaml`. The contents of 
the environment definition should be organized as follows:

[yaml]: https://en.wikipedia.org/wiki/YAML

```yaml
---
my-app-environment:
    description:
        A description of what this environment is for
    layers:
        # The layers that you environment requires. They will be deployed in the
        # same order as you list them. Note that you can also pass parameters 
        # to a layer (more on that later).
        - {layer: name_of_first_layer, layer_param: layer_value}
        - {layer: name_of_second_layer}
        - {layer: name_of_third_layer}
```

## Layer anatomy

Anything associated to a given layer must be stored in a directory with the
same name as the layer, within the same directory where the environment
_definition file_ is located. If we consider the `my-app-environment` 
environment we used above then your directory tree should look like this:

![Environment tree structure](tree.png)

A layer must contain at least two files: 

* `meta.yaml`: Meta information about the layer such as a description,
  dependencies with other layers, and layer parameters.
* `resources.yaml`: Basically a CF template with the resources that the layer
   contains.

Those two files can also be in `.json` format (`meta.json` and 
`resources.json`). Or you can add the extension `.j2` if you want the files to
be pre-processed with the [Jinja2][jinja2] template compiler.

[jinja2]: http://jinja.pocoo.org/

Below an example of how a layer `meta.yaml` may look like:

```yaml
---
meta:
    description:
        Creates a VPC, that's it
    parameters:
        vpc_cidr:
            description: The CIDR block of the VPC
            value: 10.0.0.0/16
```

Above we declare only one layer parameter: `vpc_cidr`. `humilis` will make pass
that parameter to Jinja2 when compiling any template contained in the layer. So
the `resources.yaml.j2` for that same layer may look like this:

```yaml
---
resources:
    VPC:
        Type: "AWS::EC2::VPC"
        Properties:
            CidrBlock: {{ vpc_cidr }}
```


# References

You can use references in your `meta.yaml` files to refer to thing other than
resources within the same layer (to refer to resources within a layer you can
simply use Cloudformation's [Ref][cf-ref] or [GetAtt][cf-getatt] functions).
Humilis references are used by setting the value of a layer parameter to a dict
that has a `ref` key. Below an a `meta.yaml` that refers to a resource (with
a logical name `VPC`) that is contained in another layer (called `vpc_layer`):

```yaml
---
meta:
    description:
        Creates an EC2 instance in the vpc created by the vpc layer
    dependencies:
        - vpc
    parameters:
        vpc:
            description: Physical ID of the VPC where the instance will be created
            value:
                ref: 
                    parser: layer
                    parameters:
                        layer: vpc_layer
                        resource: VPC
```

Every reference must have a `parser` key that identifies the parser that
should be used to parse the reference. The optional key `parameters` allows
you to pass parameters to the reference parser. You can pass either named
parameters (as a dict) or positional arguments (as a list). More information
on reference parsers below.


[cf-ref]: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-ref.html
[cf-getatt]: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html


## Built-in reference parsers

TBD

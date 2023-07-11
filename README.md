# soar-sdk overview 


## Authentication
## Standard Authentications 
~~~python
from soarsdk.client import PhantomClient
# Password authentication 
phantom: PhantomClient = PhantomClient(username='username', password='password')

# Token Authentication 
phantom: PhantomClient = PhantomClient(token='token_string')

~~~

## Providing an authenticated session 
For larger organizations, it might be necessary to build out a custom authentication library to handle caching and different authentication schemas outside of the standard credentials or tokens. 
~~~python 
from soarsdk.client import PhantomClient
from custom_module import authentication_function

soar_url, authenticated_session = authentication_function()
phantom: PhantomClient = PhantomClient(url=soar_url, session=authenticated_session)
~~~
See docs/auth for more information and guidance on developing an internal authentication library



### Object Variables operations 
~~~python
import soarsdk 
# Object Creation
container1 = soarsdk.objects.Container()
container1.name = 'Test Container'
container1.label = 'workbench'

container1 = soarsdk.objects.Container(name='Test Container', label='workbench')
artifact1 = soarsdk.objects.Artifact(name='test_artifact_1' label='test_label')
~~~

This methodology makes it easier to adapt future functionality. By having a PhantomObject as a dictionary, it makes it simple to grab and update any information from the API pertaining to that object.  

~~~python
import soarsdk
# establish our connection
~~~

## Using Containers and Artifacts 

### Creating Containers with Artifacts 
~~~python
# import soarsdk library 
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container

phantom: PhantomClient = PhantomClient(username='username', password='password')

container: Container = Container(name="soarsdk Library Example", label="any_label")
artifact1: Artifact = Artifact(name="soarsdk Artifact 1", label="soarsdk 1")
artifact2: Artifact = Artifact(name="soarsdk Artifact 2", label="soarsdk 2")

container.add_artifact(artifact1, artifact2)

phantom.create_container(container=container)
~~~

### Referencing an Existing Container 
To download an existing container on the server, you can initialize a container object with the "id" attribute set. The method **update_container_values** will query the API to pull back its data, artifacts, actions, playbooks, notes, etc. This can be an **expensive** query to use in a loop. 

~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container

phantom: PhantomClient = PhantomClient(username='username', password='password')

existing_container: Container = Container(id=123)

phantom.update_container_values(container)

~~~


## Working with Prompts 
Approvals for a given playbook are associated within the "Playbook" object. To define a series of prompts/approvals on a given container, create a dictionary where each key is the explict prompt_name and the value is a list of strings containing the ordered responses. Consider the following example

~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container

phantom: PhantomClient = PhantomClient(username='username', password='password')
artifact = Artifact(name='dummy', label='dummy')
container = Container(name='test', label='workbench', artifacts=[artifact])
phantom.create_container(container)

# let's define the prompts / approvals we need to match 
prompts = {
    'prompt_1': ['This is a standard response to an input', 'No', 'Apples'], 
    'prompt_2': ['Yes']
}
playbook = Playbook(name='soarsdk_prompts_test', prompts=prompts) 
container.add_playbooks(playbook)
phantom.run_playbooks(container=container)
                    
~~~

The playbook will launch and when an approval is found matching one configured on the Playbook object, it will answer the prompt with the pre-supplied responses. soarsdk doesn't rely on the order of the provided responses to map which answers should go where, instead, it uses the prompt_name configured on the playbook.



## Notes on Requests & Errors
All HTTP requests handled by the library utilize the function PhantomConnector._handle_request() which contains error handling and exception throwing based off the HTTP status code. 


## Development

### General development

1. Install a standard VS Code remote development environment https://code.visualstudio.com/docs/remote/containers#_installation (Note: Other docker-compatible providers can be used in place of Docker Desktop, such as [Rancher Desktop]<https://rancherdesktop.io/>)
2. Clone this repository and open the directory in VS Code, follow the prompt to use the embedded development container configuration

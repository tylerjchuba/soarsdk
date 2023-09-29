# soarsdk overview 
At its core, soarsdk a customer built API wrapper for the Splunk SOAR product. This tool was primarily built for use with the [soar-behaviors](https://github.com/tylerjchuba/soar-behaviors) test suite but proved invaluable for administrative tasks and larger scale projects. The goal of this project to simplify and standardize script interactions with Splunk SOAR in an object-oriented manner. 

This is the initial release and we will be adding additional functionality in the coming weeks to simplify usage even further. 


## Authentication
### Standard Authentications 
~~~python
from soarsdk.client import PhantomClient
# Password authentication 
url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

# Token Authentication 
url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, soarToken='token_string')

~~~

### Providing an authenticated session 
For larger organizations, it might be necessary to build out a custom authentication library to handle caching and different authentication schemas outside of the standard credentials or tokens. The requests.session object provided must have the appropriate CSRF token set inside the headers [(example here)](https://github.com/tylerjchuba/soarsdk/blob/e0047ebd31a435798a229a11562c7368dcab97a8/src/soarsdk/client.py#L151).

~~~python 
from soarsdk.client import PhantomClient
from custom_module import authentication_function

soar_url, authenticated_session = authentication_function()
phantom: PhantomClient = PhantomClient(url=soar_url, session=authenticated_session)
~~~

More information will be coming soon that provide guidance on credential caching & storage. 



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

### Creating Containers with Artifacts 
~~~python
# import soarsdk library 
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

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

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

existing_container: Container = Container(id=123)

phantom.update_container_values(container)

~~~


## Running Playbooks
Once you have an initialized container, there are a few different options to launch playbooks. You can define and assign the playbook to the container or provide the playbook object as a parameter. 

### Appending to the container
~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Container
from soarsdk.objects import Playbook
from soarsdk.exceptions import PlaybookException 

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

existing_container: Container = Container(id=123)

phantom.update_container_values(container)

container.playbooks.append(Playbook(name="repo/playbook_name"))

phantom.run_playbooks(existing_container)

~~~

### Running a Playbook as an arg
~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Container
from soarsdk.objects import Playbook
from soarsdk.exceptions import PlaybookException 

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

existing_container: Container = Container(id=123)

phantom.update_container_values(container)

playbook_with_asset_error: Playbook = Playbook(name="repo/playbook_name")

phantom.run_playbooks(existing_container, playbook)
~~~

### Handling Playbook Exceptions 
By default, the soarsdk.client.PhantomClient.run_playbooks() method will monitor for python exceptions & action errors. To prevent the associated exception to be thrown, use the following try/except block.  

~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Container
from soarsdk.objects import Playbook
from soarsdk.exceptions import PlaybookException 

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')

existing_container: Container = Container(id=123)

phantom.update_container_values(container)

playbook_with_asset_error: Playbook = Playbook(name="repo/playbook_name")

try:
    phantom.run_playbooks(existing_container, playbook_with_asset_error)
except PlaybookException:
    pass

~~~
## Working with Prompts 
Approvals for a given playbook are associated within the "Playbook" object. To define a series of prompts/approvals on a given container, create a dictionary where each key is the specific prompt_name and the value is a list of strings containing the ordered responses. Consider the following example

~~~python
from soarsdk.client import PhantomClient
from soarsdk.objects import Artifact, Container

url = 'https://localhost:8000"
phantom: PhantomClient = PhantomClient(url=url, username='username', password='password')
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


## Differences in Objects versus the SOAR API 
### Playbooks vs Playbook_run
Playbooks objects are a combined abstraction of the rest/playbook (configuration object in SOAR) and the rest/playbook_run (instance of the playbook running). The main purpose of this is to simplify interactions for the testing library. The soarsdk.objects.Playbook object is primarily a representation of the playbook_run endpoint 

### Action vs Action_run vs App_run
The action object is also a hybrid object from this perspective. The action is primarily an **action_run** object with some configuration items available from the the action endpoint. When pulling down results from a playbook or action's execution, it will also add the key elements from its app_execution if present. This was mainly to simplify access without having to iterate through multiples of objects and provides a similar view the GUI in mission control.  



## Notes on Requests & Errors
All HTTP requests handled by the library utilize the function PhantomConnector._handle_request() which contains error handling and exception throwing based off the HTTP status code. 


## Development

### General development

1. Install a standard VS Code remote development environment https://code.visualstudio.com/docs/remote/containers#_installation (Note: Other docker-compatible providers can be used in place of Docker Desktop, such as [Rancher Desktop](https://rancherdesktop.io/))
2. Clone this repository and open the directory in VS Code, follow the prompt to use the embedded development container configuration



### Contributor Credits 
Special thanks to the following contributors who've helped develop and grow this solution before its public release:
- [Drew Snellgrove](https://www.linkedin.com/in/d)
- [Caleb Riggs](https://www.linkedin.com/in/criggs626/) 
- [Tiara Hollins](https://www.linkedin.com/in/tiara-hollins/)

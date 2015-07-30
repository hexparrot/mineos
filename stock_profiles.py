"""A python script to manage minecraft servers
   Designed for use with MineOS: http://minecraft.codeemo.com
"""

__author__ = "William Dizon"
__license__ = "GNU GPL v3.0"
__version__ = "0.6.0"
__email__ = "wdchromium@gmail.com"
 
STOCK_PROFILES = [
    {
        'name': 'vanilla188',
        'type': 'standard_jar',
        'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.8.8/minecraft_server.1.8.8.jar',
        'save_as': 'minecraft_server.1.8.8.jar',
        'run_as': 'minecraft_server.1.8.8.jar',
        'ignore': '',
        'desc': 'official minecraft_server.jar, requires EULA acceptance'
        },
    {
        'name': 'vanilla1710',
        'type': 'standard_jar',
        'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.7.10/minecraft_server.1.7.10.jar',
        'save_as': 'minecraft_server.1.7.10.jar',
        'run_as': 'minecraft_server.1.7.10.jar',
        'ignore': '',
        'desc': 'official minecraft_server.jar, requires EULA acceptance'
        },
    {
        'name': 'vanilla179',
        'type': 'standard_jar',
        'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.7.9/minecraft_server.1.7.9.jar',
        'save_as': 'minecraft_server.1.7.9.jar',
        'run_as': 'minecraft_server.1.7.9.jar',
        'ignore': '',
        'desc': 'official minecraft_server.jar'
        },
    {
        'name': 'vanilla164',
        'type': 'standard_jar',
        'url': 'https://s3.amazonaws.com/Minecraft.Download/versions/1.6.4/minecraft_server.1.6.4.jar',
        'save_as': 'minecraft_server.jar',
        'run_as': 'minecraft_server.jar',
        'ignore': '',
        'desc': 'official minecraft_server.jar'
        }
]

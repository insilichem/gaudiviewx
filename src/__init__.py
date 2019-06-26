##############
#   GaudiViewX: UCSF ChimeraX extension to
#   explore and analyze GaudiMM solutions

#   https://github.com/insilichem/gaudiviewx

#   Copyright 2019 Andrés Giner Antón, Jaime Rodriguez-Guerra
#   and Jean-Didier Marechal

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
##############

from chimerax.core.toolshed import BundleAPI


class _MyAPI(BundleAPI):

    api_version = 1

    @staticmethod
    def start_tool(session, bi, ti):
        if ti.name == "GaudiViewX":
            from . import tool

            return tool.GaudiViewXTool(session, ti.name)
        raise ValueError("trying to start unknown tool: %s" % ti.name)

    @staticmethod
    def get_class(class_name):
        if class_name == "GaudiViewXTool":
            from . import tool

            return tool.GaudiViewXTool
        raise ValueError("Unknown class name '%s'" % class_name)


bundle_api = _MyAPI()

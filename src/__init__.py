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

import json
import logging
import xmlrpc.client
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Literal, Union, List
import requests

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent, ImageContent

# freecad_cam_mcp.py
import asyncio
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FreeCADMCPserver")


_only_text_feedback = False


# freecad_addr = "10.253.205.85"
# freecad_addr = "192.168.0.105"
# freecad_addr = "10.253.208.109"
# freecad_addr = "10.253.209.47"
# freecad_addr = "10.253.212.198"
freecad_addr = "localhost"

class FreeCADConnection:
    def __init__(self, host: str = freecad_addr, port: int = 9875):
        # Create a transport with timeout
        import socket
        transport = xmlrpc.client.Transport()
        # Set timeout on the underlying socket
        transport.timeout = 30  # 30 second timeout
        
        # Create ServerProxy with custom transport
        self.server = xmlrpc.client.ServerProxy(
            f"http://{host}:{port}", 
            allow_none=True,
            transport=transport
        )

    def ping(self) -> bool:
        return self.server.ping()

    def create_document(self, name: str) -> dict[str, Any]:
        return self.server.create_document(name)

    def create_object(self, doc_name: str, obj_data: dict[str, Any]) -> dict[str, Any]:
        return self.server.create_object(doc_name, obj_data)

    def edit_object(self, doc_name: str, obj_name: str, obj_data: dict[str, Any]) -> dict[str, Any]:
        return self.server.edit_object(doc_name, obj_name, obj_data)

    def delete_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return self.server.delete_object(doc_name, obj_name)

    def insert_part_from_library(self, relative_path: str) -> dict[str, Any]:
        return self.server.insert_part_from_library(relative_path)

    def execute_code(self, code: str) -> dict[str, Any]:
        return self.server.execute_code(code)

    def get_active_screenshot(self, view_name: str = "Isometric") -> str | None:
        try:
            # Check if we're in a view that supports screenshots
            result = self.server.execute_code("""
import FreeCAD
import FreeCADGui

if FreeCAD.Gui.ActiveDocument and FreeCAD.Gui.ActiveDocument.ActiveView:
    view_type = type(FreeCAD.Gui.ActiveDocument.ActiveView).__name__
    
    # These view types don't support screenshots
    unsupported_views = ['SpreadsheetGui::SheetView', 'DrawingGui::DrawingView', 'TechDrawGui::MDIViewPage']
    
    if view_type in unsupported_views or not hasattr(FreeCAD.Gui.ActiveDocument.ActiveView, 'saveImage'):
        print("Current view does not support screenshots")
        False
    else:
        print(f"Current view supports screenshots: {view_type}")
        True
else:
    print("No active view")
    False
""")

            # If the view doesn't support screenshots, return None
            if not result.get("success", False) or "Current view does not support screenshots" in result.get("message", ""):
                logger.info("Screenshot unavailable in current view (likely Spreadsheet or TechDraw view)")
                return None

            # Otherwise, try to get the screenshot
            return self.server.get_active_screenshot(view_name)
        except Exception as e:
            # Log the error but return None instead of raising an exception
            logger.error(f"Error getting screenshot: {e}")
            return None

    def get_objects(self, doc_name: str) -> list[dict[str, Any]]:
        try:
            return self.server.get_objects(doc_name)
        except xmlrpc.client.ProtocolError as e:
            logger.error(f"XML-RPC protocol error getting objects: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting objects: {e}")
            raise

    def get_object(self, doc_name: str, obj_name: str) -> dict[str, Any]:
        return self.server.get_object(doc_name, obj_name)

    def get_parts_list(self) -> list[str]:
        return self.server.get_parts_list()

    def disconnect(self):
        self.server.disconnect()

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    try:
        logger.info("FreeCADMCP server starting up")
        try:
            _ = get_freecad_connection()
            logger.info("Successfully connected to FreeCAD on startup")
        except Exception as e:
            logger.warning(f"Could not connect to FreeCAD on startup: {str(e)}")
            logger.warning(
                "Make sure the FreeCAD addon is running before using FreeCAD resources or tools"
            )
        yield {}
    finally:
        # Clean up the global connection on shutdown
        global _freecad_connection
        if _freecad_connection:
            logger.info("Disconnecting from FreeCAD on shutdown")
            # _freecad_connection.disconnect()
            _freecad_connection = None
        logger.info("FreeCADMCP server shut down")


mcp = FastMCP(
    "FreeCADMCP",
    lifespan=server_lifespan,
)

_freecad_connection: FreeCADConnection | None = None


def get_freecad_connection():
    """Get or create a persistent FreeCAD connection"""
    global _freecad_connection
    if _freecad_connection is None:
        _freecad_connection = FreeCADConnection(host=freecad_addr, port=9875)
        if not _freecad_connection.ping():
            logger.error("Failed to ping FreeCAD")
            _freecad_connection = None
            raise Exception(
                "Failed to connect to FreeCAD. Make sure the FreeCAD addon is running."
            )
    return _freecad_connection


# Helper function to safely add screenshot to response
def add_screenshot_if_available(response, screenshot):
    """Safely add screenshot to response only if it's available"""
    if screenshot is not None and not _only_text_feedback:
        response.append(ImageContent(type="image", data=screenshot, mimeType="image/png"))
    elif not _only_text_feedback:
        # Add an informative message that will be seen by the AI model and user
        response.append(TextContent(
            type="text", 
            text="Note: Visual preview is unavailable in the current view type (such as TechDraw or Spreadsheet). "
                 "Switch to a 3D view to see visual feedback."
            # text=""
        ))
    return response


@mcp.tool()
def create_document(ctx: Context, name: str) -> list[TextContent]:
    """Create a new FreeCAD document (CAD design file).
    Use this tool to create a new CAD document for 3D modeling.
    For creating file system directories/folders, use the create_directory tool instead.

    Args:
        name: The name of the FreeCAD document to create (e.g., "MyDesign", "Part1").

    Returns:
        A message indicating the success or failure of the document creation.

    Examples:
        If you want to create a document named "MyDocument", you can use the following data.
        ```json
        {
            "name": "MyDocument"
        }
        ```
    """

    freecad = get_freecad_connection()
    try:
        res = freecad.create_document(name)
        if res["success"]:
            return [
                TextContent(type="text", text=f"Document '{res['document_name']}' created successfully")
            ]
        else:
            return [
                TextContent(type="text", text=f"Failed to create document: {res['error']}")
            ]
    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to create document: {str(e)}")
        ]


@mcp.tool()
def create_object(
    ctx: Context,
    doc_name: str,
    obj_type: str,
    obj_name: str,
    analysis_name: str | None = None,
    obj_properties: dict[str, Any] = None,
) -> list[TextContent | ImageContent]:
    """Create a new object in FreeCAD.
    Object type is starts with "Part::" or "Draft::" or "PartDesign::" or "Fem::".

    Args:
        doc_name: The name of the document to create the object in.
        obj_type: The type of the object to create (e.g. 'Part::Box', 'Part::Cylinder', 'Draft::Circle', 'PartDesign::Body', etc.).
        obj_name: The name of the object to create.
        obj_properties: The properties of the object to create.

    Returns:
        A message indicating the success or failure of the object creation and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        obj_data = {"Name": obj_name, "Type": obj_type, "Properties": obj_properties or {}, "Analysis": analysis_name}
        res = freecad.create_object(doc_name, obj_data)
        screenshot = freecad.get_active_screenshot()
        
        if res["success"]:
            response = [
                TextContent(type="text", text=f"Object '{res['object_name']}' created successfully"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to create object: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to create object: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to create object: {str(e)}")
        ]


@mcp.tool()
def edit_object(
    ctx: Context, doc_name: str, obj_name: str, obj_properties: dict[str, Any]
) -> list[TextContent | ImageContent]:
    """Edit an object in FreeCAD.
    This tool is used when the `create_object` tool cannot handle the object creation.

    Args:
        doc_name: The name of the document to edit the object in.
        obj_name: The name of the object to edit.
        obj_properties: The properties of the object to edit.

    Returns:
        A message indicating the success or failure of the object editing and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.edit_object(doc_name, obj_name, obj_properties)
        screenshot = freecad.get_active_screenshot()
        
        if res["success"]:
            response = [
                TextContent(type="text", text=f"Object '{res['object_name']}' edited successfully"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to edit object: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to edit object: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to edit object: {str(e)}")
        ]


@mcp.tool()
def delete_object(ctx: Context, doc_name: str, obj_name: str) -> list[TextContent | ImageContent]:
    """Delete an object in FreeCAD.

    Args:
        doc_name: The name of the document to delete the object from.
        obj_name: The name of the object to delete.

    Returns:
        A message indicating the success or failure of the object deletion and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.delete_object(doc_name, obj_name)
        screenshot = freecad.get_active_screenshot()
        
        if res["success"]:
            response = [
                TextContent(type="text", text=f"Object '{res['object_name']}' deleted successfully"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to delete object: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to delete object: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to delete object: {str(e)}")
        ]


@mcp.tool()
def execute_code(ctx: Context, code: str) -> list[TextContent | ImageContent]:
    """Execute arbitrary Python code in FreeCAD.

    Args:
        code: The Python code to execute.

    Returns:
        A message indicating the success or failure of the code execution, the output of the code execution, and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.execute_code(code)
        screenshot = freecad.get_active_screenshot()
        
        if res["success"]:
            response = [
                TextContent(type="text", text=f"Code executed successfully: {res['message']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to execute code: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to execute code: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to execute code: {str(e)}")
        ]


@mcp.tool()
def get_view(ctx: Context, view_name: Literal["Isometric", "Front", "Top", "Right", "Back", "Left", "Bottom", "Dimetric", "Trimetric"]) -> list[ImageContent | TextContent]:
    """Get a screenshot of the active view.

    Args:
        view_name: The name of the view to get the screenshot of.
        The following views are available:
        - "Isometric"
        - "Front"
        - "Top"
        - "Right"
        - "Back"
        - "Left"
        - "Bottom"
        - "Dimetric"
        - "Trimetric"

    Returns:
        A screenshot of the active view.
    """
    freecad = get_freecad_connection()
    screenshot = freecad.get_active_screenshot(view_name)
    
    if screenshot is not None:
        return [ImageContent(type="image", data=screenshot, mimeType="image/png")]
    else:
        return [TextContent(type="text", text="Cannot get screenshot in the current view type (such as TechDraw or Spreadsheet)")]


@mcp.tool()
def insert_part_from_library(ctx: Context, relative_path: str) -> list[TextContent | ImageContent]:
    """Insert a part from the parts library addon.

    Args:
        relative_path: The relative path of the part to insert.

    Returns:
        A message indicating the success or failure of the part insertion and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.insert_part_from_library(relative_path)
        screenshot = freecad.get_active_screenshot()
        
        if res["success"]:
            response = [
                TextContent(type="text", text=f"Part inserted from library: {res['message']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to insert part from library: {res['error']}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to insert part from library: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to insert part from library: {str(e)}")
        ]


@mcp.tool()
def get_objects(ctx: Context, doc_name: str) -> list[TextContent | ImageContent]:
    """Get all objects in a document.
    You can use this tool to get the objects in a document to see what you can check or edit.

    Args:
        doc_name: The name of the document to get the objects from.

    Returns:
        A list of objects in the document and a screenshot of the document.
    """
    freecad = get_freecad_connection()
    try:
        screenshot = freecad.get_active_screenshot()
        response = [
            TextContent(type="text", text=json.dumps(freecad.get_objects(doc_name))),
        ]
        return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to get objects: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to get objects: {str(e)}")
        ]


@mcp.tool()
def get_object(ctx: Context, doc_name: str, obj_name: str) -> list[TextContent | ImageContent]:
    """Get an object from a document.
    You can use this tool to get the properties of an object to see what you can check or edit.

    Args:
        doc_name: The name of the document to get the object from.
        obj_name: The name of the object to get.

    Returns:
        The object and a screenshot of the object.
    """
    freecad = get_freecad_connection()
    try:
        screenshot = freecad.get_active_screenshot()
        response = [
            TextContent(type="text", text=json.dumps(freecad.get_object(doc_name, obj_name))),
        ]
        return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to get object: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to get object: {str(e)}")
        ]


def get_http(question):
    url = "http://10.50.10.53:8009/query"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "question": question
        }
    res = {'msg': "", 'code': 0, 'parts': []}
    try:
        # Add timeout to prevent hanging requests
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),  # 使用json.dumps确保数据格式正确，ensure_ascii=False支持中文
            timeout=10  # 10 second timeout for connection and read
        )
        # 检查响应状态
        if response.status_code == 200:
            try:
                response_data = response.json()
                if 'answer' in response_data:
                    res['parts'] = response_data['answer']
                    logger.info(f"HTTP request successful, got {len(res['parts'])} parts")
                else:
                    logger.error(f"HTTP response missing 'answer' key: {response_data}")
                    res['msg'] = "Response missing 'answer' key"
                    res['code'] = -1
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                res['msg'] = f"Invalid JSON response: {str(e)}"
                res['code'] = -1
        else:
            logger.error(f"HTTP request failed with status code: {response.status_code}")
            logger.error(f"Error response: {response.text[:200]}")
            res['msg'] = f"HTTP error {response.status_code}"
            res['code'] = -1

    except requests.exceptions.Timeout:
        logger.error("HTTP request timed out after 10 seconds")
        res['msg'] = "请求超时"
        res['code'] = -1
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request exception: {str(e)}")
        res['msg'] = str(e)
        res['code'] = -1
    except Exception as e:
        logger.error(f"Unexpected error in get_http: {str(e)}")
        res['msg'] = str(e)
        res['code'] = -1

    return res


@mcp.tool()
def get_parts_list(ctx: Context, inputs) -> list[TextContent]:
    """Get the list of parts in the parts library addon.

    Args:
        inputs: the user inputs.

    """
    try:
        # freecad = get_freecad_connection()
        # parts = freecad.get_parts_list()
        http_result = get_http(inputs)
        parts = http_result.get('parts', [])
        # with open('/Users/songyuan/Documents/projects/lab/zhipu/cad_generation/download/freecad-mcp/src/freecad_mcp/1', 'w') as f:
        #     f.write(f"{ctx} {inputs}, {parts}")
        if parts:
            return [
                TextContent(type="text", text=json.dumps(parts))
            ]
        else:
            return [
                TextContent(type="text", text=f"No parts found in the parts library. You must add parts_library addon. Error: {http_result.get('msg', 'Unknown error')}")
            ]
    except Exception as e:
        logger.error(f"Error in get_parts_list: {str(e)}")
        return [
            TextContent(type="text", text=f"Error getting parts list: {str(e)}")
        ]


@mcp.tool()
def set_freecad_spreadsheet_param(
    ctx: Context,
    doc_name: str,
    sheet_name_internal: str,
    cell_address: str,
    new_value: Union[str, float, int]
) -> List[TextContent | ImageContent]:
    """
    修改FreeCAD文档中指定Spreadsheet的带有别名的单元格的值。
    修改后将触发文档的重新计算。

    Args:
        doc_name: FreeCAD文档的名称。
        sheet_name_internal: Spreadsheet对象的内部名称 (例如 "Spreadsheet")。
                             可以通过 get_freecad_spreadsheet_params 获取此值，请查找“工作表内部名称 (Sheet Internal Name)”字段。
        cell_address: 单元格的地址 (例如 "B10")。可以通过 get_freecad_spreadsheet_params 获取。
        new_value: 要设置的新值。可以是字符串、浮点数或整数。
                   FreeCAD会尝试根据值自动推断类型。

    Returns:
        一个消息指示操作的成功或失败，以及一个屏幕截图。

    Examples:
        要将文档 "MyProject" 中内部名称为 "Spreadsheet001" 的Spreadsheet的 "B10" 单元格的值设置为 50：
        (假设通过 get_freecad_spreadsheet_params 查到 "cfg" 标签对应内部名称 "Spreadsheet001")
        ```json
        {
            "doc_name": "MyProject",
            "sheet_name_internal": "Spreadsheet001",
            "cell_address": "B10",
            "new_value": 50
        }
        ```
    """
    freecad = get_freecad_connection()
    try:
        res = freecad.set_spreadsheet_param(doc_name, sheet_name_internal, cell_address, new_value)
        
        # 截取屏幕
        screenshot = freecad.get_active_screenshot()

        if res.get("success"):
            response = [
                TextContent(type="text", text=f"成功: {res.get('message')}")
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"修改参数失败: {res.get('error', '未知错误')}")
            ]
            return add_screenshot_if_available(response, screenshot)

    except Exception as e:
        logger.error(f"Failed to set spreadsheet param: {str(e)}")
        return [
            TextContent(type="text", text=f"修改FreeCAD Spreadsheet参数失败: {str(e)}")
        ]


@mcp.tool()
def generate_gcode(
    ctx: Context,
    doc_name: str,
    job_name: str,
    output_file: str = None,
    post_processor: str = "linuxcnc"
) -> list[TextContent | ImageContent]:
    """Generate G-code from a CAM job in FreeCAD.

    Args:
        doc_name: The name of the document containing the CAM job.
        job_name: The name of the CAM job object.
        output_file: The output file path for the G-code. If not provided, a default name will be used.
        post_processor: The post-processor to use for G-code generation (e.g., 'linuxcnc', 'grbl').

    Returns:
        A message indicating the success or failure of the G-code generation and a screenshot of the result.
    """
    freecad = get_freecad_connection()
    try:
        # 设置输出文件路径
        if not output_file:
            output_file = f"/tmp/{job_name}.nc"
        
        code = f"""
def generate_gcode():
    import FreeCAD
    import Path
    
    doc = FreeCAD.getDocument("{doc_name}")
    if not doc:
        return {{"success": False, "error": f"文档 '{doc_name}' 未找到"}}
    
    job = doc.getObject("{job_name}")
    if not job:
        return {{"success": False, "error": f"作业 '{job_name}' 未找到"}}
    
    # 设置输出文件路径
    output_file = "{output_file}"
    
    try:
        # 尝试不同的 G-code 生成方法
        # 方法1: 使用作业的 Path 属性生成 G 代码
        if hasattr(job, 'Path') and job.Path:
            print('1'*10)
            gcode_content = job.Path.toGCode()
            print('gcode内容-gcode_content：', gcode_content)
            with open(output_file, 'w') as f:
                f.write(gcode_content)
            result = True
        # 方法2: 使用 Path 模块的 write 方法
        elif hasattr(Path, 'write'):
            print('2'*10)
            result = Path.write(job, output_file)
        # 方法3: 使用 Path 模块的 postProcess 方法
        elif hasattr(Path, 'postProcess'):
            print('3'*10)
            result = Path.postProcess(job, output_file, "{post_processor}")
        # 方法4: 使用 PathScripts 模块
        elif hasattr(Path, 'Scripts'):
            print('4'*10)
            import PathScripts
            if hasattr(PathScripts, 'post'):
                result = PathScripts.post.postProcess(job, output_file, "{post_processor}")
            else:
                return {{"success": False, "error": "PathScripts.post 模块未找到"}}
        else:
            return {{"success": False, "error": "FreeCAD 的 CAM 模块未找到合适的 G-code 生成方法"}}
        
        if result:
            print('gcode内容1：', result)
            print()
            return {{"success": True, "message": f"G-code 生成成功: {{output_file}}", "output_file": output_file}}
        else:
            return {{"success": False, "error": "G-code 生成失败"}}
            
    except Exception as e:
        return {{"success": False, "error": f"G-code 生成过程中出错: {{str(e)}}"}}

result = generate_gcode()
print('gcode内容：', result)
print(result)
"""
        res = freecad.execute_code(code)
        screenshot = freecad.get_active_screenshot()
        
        if res.get("success", False):
            response = [
                TextContent(type="text", text=f"G-code generation completed: {res.get('message', '')}"),
            ]
            return add_screenshot_if_available(response, screenshot)
        else:
            response = [
                TextContent(type="text", text=f"Failed to generate G-code: {res.get('error', 'Unknown error')}"),
            ]
            return add_screenshot_if_available(response, screenshot)
    except Exception as e:
        logger.error(f"Failed to generate G-code: {str(e)}")
        return [
            TextContent(type="text", text=f"Failed to generate G-code: {str(e)}")
        ]


@mcp.prompt()
def asset_creation_strategy() -> str:
    return """
Asset Creation Strategy for FreeCAD MCP

When creating content in FreeCAD, always follow these steps:

0. Before starting any task, always use get_objects() to confirm the current state of the document.

1. Utilize the parts library:
   - Check available parts using get_parts_list().
   - If the required part exists in the library, use insert_part_from_library() to insert it into your document.

2. If the appropriate asset is not available in the parts library:
   - Create basic shapes (e.g., cubes, cylinders, spheres) using create_object().
   - Adjust and define detailed properties of the shapes as necessary using edit_object().

3. Always assign clear and descriptive names to objects when adding them to the document.

4. Explicitly set the position, scale, and rotation properties of created or inserted objects using edit_object() to ensure proper spatial relationships.

5. After editing an object, always verify that the set properties have been correctly applied by using get_object().

6. If detailed customization or specialized operations are necessary, use execute_code() to run custom Python scripts.

Only revert to basic creation methods in the following cases:
- When the required asset is not available in the parts library.
- When a basic shape is explicitly requested.
- When creating complex shapes requires custom scripting.

FreeCAD Parameter Modification Strategy:

When modifying parameters in FreeCAD:
1. To view available parameters from Spreadsheets, use the `get_freecad_spreadsheet_params()` tool.
   This will return a list of all aliased parameters. For each parameter, the output will clearly show:
   - "别名 (Alias)"
   - "工作表标签 (Sheet Label)" (This is the name you see in FreeCAD's UI)
   - "工作表内部名称 (Sheet Internal Name)" (This is the name required by the `set_freecad_spreadsheet_param` tool)
   - "单元格地址 (Cell Address)"
   - "当前值 (Current Value)"
2. To modify a specific parameter, use the `set_freecad_spreadsheet_param()` tool. You MUST provide the `doc_name`, the `sheet_name_internal` (obtained from step 1), the `cell_address`, and the `new_value`.
"""


def main():
    """Run the MCP server"""
    global _only_text_feedback
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-text-feedback", action="store_true", help="Only return text feedback")
    parser.add_argument('--ip',
            type=str,
            default="localhost",  # Example default port
            help='ip'
    )
    
    # parser.add_argument(
    #     "--ip",
    #     dest="host",  # --ip 是 --host 的别名
    #     help="Alias for --host. Example: 192.168.1.100"
    # )
    args = parser.parse_args()

    _only_text_feedback = args.only_text_feedback

    global freecad_addr
    freecad_addr = args.ip
    logger.info(f"Only text feedback: {_only_text_feedback}")
    
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"MCP server crashed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Exit with error code
        sys.exit(1)


def test_execute_code():
    """
    测试 execute_code MCP 工具的方法
    
    这个测试方法可以用于验证 execute_code 工具的功能是否正常。
    它创建了一个完整的测试场景，执行 Python 代码并验证结果。
    """
    import sys
    import os
    import time
    
    # 添加当前目录到 Python 路径，以便导入模块
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    test_results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0
    }
    
    def run_test(test_name, test_func):
        """运行单个测试并记录结果"""
        test_results["total"] += 1
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            if result:
                test_results["passed"] += 1
                print(f"✅ 通过 - 耗时: {end_time - start_time:.2f}秒")
            else:
                test_results["failed"] += 1
                print(f"❌ 失败 - 耗时: {end_time - start_time:.2f}秒")
                
        except Exception as e:
            test_results["errors"] += 1
            print(f"💥 错误 - {e}")
            import traceback
            traceback.print_exc()
    
    try:
        # 创建 FreeCAD 连接
        print("正在连接到 FreeCAD...")
        freecad = FreeCADConnection(host=freecad_addr, port=9875)
        
        # 测试连接
        if not freecad.ping():
            print("❌ 无法连接到 FreeCAD")
            return False
        
        print("✅ 成功连接到 FreeCAD")
        
        # 测试 1: 简单的 Python 代码执行
        def test_basic_code():
            code = """
print("Hello from FreeCAD!")
result = 2 + 3
print(f"2 + 3 = {result}")
result
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "Hello from FreeCAD!" in res.get("message", "")
        
        run_test("基本代码执行", test_basic_code)
        
        # 测试 2: 创建几何体
        def test_create_geometry():
            code = """
import FreeCAD
doc = FreeCAD.newDocument("TestDocument")
box = doc.addObject("Part::Box", "TestBox")
box.Length = 10
box.Width = 10
box.Height = 10
doc.recompute()
print(f"创建了盒子: {box.Name}")
box.Name
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "创建了盒子: TestBox" in res.get("message", "")
        
        run_test("创建几何体", test_create_geometry)
        
        # 测试 3: 获取文档信息
        def test_get_document_info():
            code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc:
    objects = [obj.Name for obj in doc.Objects]
    print(f"文档中的对象: {objects}")
    objects
else:
    print("没有活动文档")
    []
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "文档中的对象: ['TestBox']" in res.get("message", "")
        
        run_test("获取文档信息", test_get_document_info)
        
        # 测试 4: 复杂几何操作
        def test_complex_geometry():
            code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc:
    # 创建圆柱体
    cylinder = doc.addObject("Part::Cylinder", "TestCylinder")
    cylinder.Radius = 5
    cylinder.Height = 15
    cylinder.Placement.Base = FreeCAD.Vector(20, 0, 0)
    
    # 创建球体
    sphere = doc.addObject("Part::Sphere", "TestSphere")
    sphere.Radius = 8
    sphere.Placement.Base = FreeCAD.Vector(40, 0, 0)
    
    doc.recompute()
    print(f"创建了复杂几何体: {[obj.Name for obj in doc.Objects]}")
    len(doc.Objects)
else:
    print("没有活动文档")
    0
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "创建了复杂几何体:" in res.get("message", "")
        
        run_test("复杂几何操作", test_complex_geometry)
        
        # 测试 5: 数学计算
        def test_math_calculations():
            code = """
import math
# 计算圆的面积
radius = 10
area = math.pi * radius ** 2
print(f"半径为 {radius} 的圆面积: {area:.2f}")
area
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "圆面积: 314.16" in res.get("message", "")
        
        run_test("数学计算", test_math_calculations)
        
        # 测试 6: 列表操作
        def test_list_operations():
            code = """
# 创建和操作列表
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]
print(f"原始列表: {numbers}")
print(f"平方列表: {squared}")
sum(squared)
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "原始列表: [1, 2, 3, 4, 5]" in res.get("message", "")
        
        run_test("列表操作", test_list_operations)
        
        # 测试 7: 错误处理测试
        def test_error_handling():
            code = """
# 这行代码会引发错误
undefined_variable
"""
            res = freecad.execute_code(code)
            # 错误处理应该返回 success=False
            return not res.get("success", False) and "error" in res
        
        run_test("错误处理", test_error_handling)
        
        # 测试 8: 导入模块测试
        def test_module_import():
            code = """
import random
numbers = [random.randint(1, 100) for _ in range(5)]
print(f"随机数: {numbers}")
len(numbers)
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "随机数:" in res.get("message", "")
        
        run_test("模块导入", test_module_import)
        
        # 测试 9: 字符串操作
        def test_string_operations():
            code = """
text = "Hello FreeCAD World"
words = text.split()
reversed_text = ' '.join(reversed(words))
print(f"原始文本: {text}")
print(f"反转文本: {reversed_text}")
reversed_text
"""
            res = freecad.execute_code(code)
            return res.get("success", False) and "World FreeCAD Hello" in res.get("message", "")
        
        run_test("字符串操作", test_string_operations)
        
        # 测试 10: 清理测试文档
        def test_cleanup():
            code = """
import FreeCAD
doc = FreeCAD.ActiveDocument
if doc:
    doc_name = doc.Name
    FreeCAD.closeDocument(doc_name)
    print(f"已关闭文档: {doc_name}")
    True
else:
    print("没有活动文档")
    False
"""
            res = freecad.execute_code(code)
            return res.get("success", False)
        
        run_test("清理测试文档", test_cleanup)
        
        # 输出测试总结
        print(f"\n{'='*50}")
        print("测试总结")
        print(f"{'='*50}")
        print(f"总测试数: {test_results['total']}")
        print(f"✅ 通过: {test_results['passed']}")
        print(f"❌ 失败: {test_results['failed']}")
        print(f"💥 错误: {test_results['errors']}")
        
        success_rate = (test_results['passed'] / test_results['total']) * 100 if test_results['total'] > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        
        if test_results['failed'] == 0 and test_results['errors'] == 0:
            print("\n🎉 所有测试通过！execute_code 工具功能正常。")
            return True
        else:
            print(f"\n⚠️  有 {test_results['failed']} 个测试失败，{test_results['errors']} 个错误。")
            return False
        
    except Exception as e:
        print(f"💥 测试过程中出现严重错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cam_job():
    """测试 CAM 作业创建功能"""
    code1 = """
def test():
    doc_name = "Truck1"
    base_object_name = "FrontWheel2"
    job_name = "job1"

    import FreeCAD
    import Path
    
    doc = FreeCAD.getDocument(doc_name)
    if not doc:
        return {"success": False, "error": f"文档 '{doc_name}' 未找到"}
    
    base_object = doc.getObject(base_object_name)
    if not base_object:
        return {"success": False, "error": f"基础对象 '{base_object_name}' 未找到"}
    
    # 创建简单的 CAM 作业对象
    job = doc.addObject("Path::Feature", job_name)
    job.Label = job_name
    
    # 设置基础模型引用
    if hasattr(job, 'Base'):
        job.Base = base_object
    
    # 设置作业属性
    if 'job_properties' in locals() and job_properties:
        for prop, value in job_properties.items():
            if hasattr(job, prop):
                setattr(job, prop, value)
    
    doc.recompute()
    return {"success": True, "job_name": job.Name}

result = test()
print(result)
print('8'*100)

"""
    freecad = FreeCADConnection(host=freecad_addr, port=9875)
    res1 = freecad.execute_code(code1)
    print(f"结果: {res1}")
    return res1.get("success", False)


if __name__ == "__main__":
    # 如果直接运行此文件，可以选择运行测试
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("运行 execute_code 测试...")
        test_execute_code()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-cam":
        print("运行 CAM 作业测试...")
        test_cam_job()
    else:
        main()



"""
/Users/songyuan/Documents/projects/lab/zhipu/AGENT/平台类/自动生成workflow/cad-lg-mcp-agents/version1/MCP/freecad-mcp/src/freecad_mcp/server.py


"""

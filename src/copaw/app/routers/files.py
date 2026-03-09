# -*- coding: utf-8 -*-
"""File Management API – browse, upload, download, delete files in WORKING_DIR."""

from __future__ import annotations

import os
import mimetypes
import shutil
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ...constant import WORKING_DIR

router = APIRouter(prefix="/files", tags=["files"])

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class FileItem(BaseModel):
    """File information model."""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Relative path from WORKING_DIR")
    full_path: str = Field(..., description="Absolute path")
    is_dir: bool = Field(..., description="Whether it's a directory")
    size: Optional[int] = Field(None, description="File size in bytes (None for directories)")
    mtime: float = Field(..., description="Last modification timestamp")
    mtime_str: str = Field(..., description="Formatted modification time")
    type: str = Field(..., description="File type (file, directory, symlink)")
    extension: Optional[str] = Field(None, description="File extension")
    mime_type: Optional[str] = Field(None, description="MIME type")
    permissions: str = Field(..., description="File permissions in octal")

class FileListResponse(BaseModel):
    """Response model for file list."""
    success: bool = Field(..., description="Whether the operation succeeded")
    data: List[FileItem] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    current_path: str = Field(..., description="Current directory path")
    parent_path: Optional[str] = Field(None, description="Parent directory path")
    message: Optional[str] = Field(None, description="Optional message")

class FileContentResponse(BaseModel):
    """Response model for file content."""
    success: bool = Field(..., description="Whether the operation succeeded")
    content: Optional[str] = Field(None, description="File content")
    encoding: Optional[str] = Field(None, description="File encoding")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    message: Optional[str] = Field(None, description="Optional message")

class FileOperationResponse(BaseModel):
    """Response model for file operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Operation result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _is_safe_path(base_path: Path, target_path: Path) -> bool:
    """Check if target_path is within base_path to prevent directory traversal."""
    try:
        base_resolved = base_path.resolve()
        
        # First check if the path itself (without resolving symlinks) is within base
        # This allows symbolic links that point outside but are inside WORKING_DIR
        try:
            target_relative = target_path.relative_to(base_path)
            # If we can get a relative path without resolving, it's safe
            return True
        except ValueError:
            # If not, try resolving and checking
            target_resolved = target_path.resolve()
            return str(target_resolved).startswith(str(base_resolved))
    except Exception:
        return False

def _get_file_info(file_path: Path, base_path: Path) -> FileItem:
    """Get file information for a single file."""
    stat_info = file_path.stat()
    
    # Get relative path
    try:
        rel_path = file_path.relative_to(base_path).as_posix()
    except ValueError:
        rel_path = file_path.name
    
    # Determine file type
    if file_path.is_dir():
        file_type = "directory"
        size = None
    elif file_path.is_symlink():
        file_type = "symlink"
        size = stat_info.st_size
    else:
        file_type = "file"
        size = stat_info.st_size
    
    # Get file extension
    extension = None
    if file_path.is_file():
        suffix = file_path.suffix
        if suffix:
            extension = suffix.lower()[1:]  # Remove the dot
    
    # Get MIME type
    mime_type = None
    if file_path.is_file():
        mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # Format permissions
    permissions = oct(stat_info.st_mode)[-3:]
    
    # Format modification time
    mtime_dt = datetime.fromtimestamp(stat_info.st_mtime)
    mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    return FileItem(
        name=file_path.name,
        path=rel_path,
        full_path=str(file_path),
        is_dir=file_path.is_dir(),
        size=size,
        mtime=stat_info.st_mtime,
        mtime_str=mtime_str,
        type=file_type,
        extension=extension,
        mime_type=mime_type,
        permissions=permissions,
    )

def _filter_files(files: List[FileItem], keyword: str = "", file_type: str = "") -> List[FileItem]:
    """Filter files based on keyword and file type."""
    filtered = files
    
    # Filter by keyword
    if keyword:
        keyword_lower = keyword.lower()
        filtered = [f for f in filtered if keyword_lower in f.name.lower()]
    
    # Filter by file type
    if file_type:
        if file_type == "directory":
            filtered = [f for f in filtered if f.is_dir]
        elif file_type == "file":
            filtered = [f for f in filtered if not f.is_dir]
        elif file_type == "image":
            filtered = [f for f in filtered if f.mime_type and f.mime_type.startswith("image/")]
        elif file_type == "text":
            filtered = [f for f in filtered if f.mime_type and f.mime_type.startswith("text/")]
        elif file_type == "code":
            code_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".html", ".css", 
                              ".json", ".yaml", ".yml", ".md", ".txt", ".xml"}
            filtered = [f for f in filtered if f.extension and f.extension in code_extensions]
    
    return filtered

def _sort_files(files: List[FileItem], sort_by: str = "name", sort_order: str = "ascend") -> List[FileItem]:
    """Sort files based on sort_by and sort_order."""
    reverse = sort_order.lower() == "descend"
    
    if sort_by == "name":
        return sorted(files, key=lambda x: x.name.lower(), reverse=reverse)
    elif sort_by == "size":
        # Directories first, then by size
        dirs = [f for f in files if f.is_dir]
        non_dirs = [f for f in files if not f.is_dir]
        dirs_sorted = sorted(dirs, key=lambda x: x.name.lower())
        non_dirs_sorted = sorted(non_dirs, key=lambda x: x.size or 0, reverse=reverse)
        return dirs_sorted + non_dirs_sorted
    elif sort_by == "mtime":
        return sorted(files, key=lambda x: x.mtime, reverse=reverse)
    elif sort_by == "type":
        return sorted(files, key=lambda x: (x.type, x.name.lower()), reverse=reverse)
    else:
        return files

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/list",
    response_model=FileListResponse,
    summary="Get file list",
    description="Get list of files and directories in the specified path.",
)
async def get_file_list(
    path: str = Query("", description="Directory path relative to WORKING_DIR"),
    keyword: str = Query("", description="Search keyword for file names"),
    file_type: str = Query("", description="Filter by file type (directory, file, image, text, code)"),
    sort_by: str = Query("name", description="Sort field (name, size, mtime, type)"),
    sort_order: str = Query("ascend", description="Sort order (ascend, descend)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> FileListResponse:
    """
    Get list of files and directories.
    """
    try:
        # Build target path - don't resolve yet for security check
        if path:
            target_path = WORKING_DIR / path
        else:
            target_path = WORKING_DIR
        
        # Security check - check without resolving first
        if not _is_safe_path(WORKING_DIR, target_path):
            raise HTTPException(
                status_code=403,
                detail="Access to this path is not allowed",
            )
        
        # Now resolve for actual operations
        target_path_resolved = target_path.resolve()
        
        # Check if path exists
        if not target_path_resolved.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Path does not exist: {path}",
            )
        
        # Check if it's a directory
        if not target_path_resolved.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {path}",
            )
        
        # Get all files and directories
        file_items = []
        for entry in target_path_resolved.iterdir():
            try:
                file_info = _get_file_info(entry, WORKING_DIR)
                file_items.append(file_info)
            except (PermissionError, OSError):
                # Skip files we can't access
                continue
        
        # Apply filters
        filtered_items = _filter_files(file_items, keyword, file_type)
        
        # Apply sorting
        sorted_items = _sort_files(filtered_items, sort_by, sort_order)
        
        # Apply pagination
        total = len(sorted_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = sorted_items[start_idx:end_idx]
        
        # Get parent path
        parent_path = None
        if target_path != WORKING_DIR:
            try:
                parent_rel = target_path.parent.relative_to(WORKING_DIR)
                parent_path = parent_rel.as_posix()
            except ValueError:
                parent_path = ""
        
        return FileListResponse(
            success=True,
            data=paginated_items,
            total=total,
            current_path=path,
            parent_path=parent_path,
            message=f"Found {total} items",
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file list: {exc}",
        )

@router.get(
    "/content/{file_path:path}",
    response_model=FileContentResponse,
    summary="Get file content",
    description="Get content of a file. For text files, returns content as string. For binary files, returns download URL.",
)
async def get_file_content(
    file_path: str,
    encoding: str = Query("utf-8", description="File encoding for text files"),
) -> FileContentResponse:
    """
    Get file content.
    """
    try:
        # Build target path
        target_path = (WORKING_DIR / file_path).resolve()
        
        # Security check
        if not _is_safe_path(WORKING_DIR, target_path):
            raise HTTPException(
                status_code=403,
                detail="Access to this file is not allowed",
            )
        
        # Check if file exists
        if not target_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File does not exist: {file_path}",
            )
        
        # Check if it's a file
        if not target_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a file: {file_path}",
            )
        
        # Get file info
        stat_info = target_path.stat()
        file_size = stat_info.st_size
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(target_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Check if it's a text file
        is_text_file = mime_type.startswith("text/") or mime_type in [
            "application/json",
            "application/xml",
            "application/javascript",
            "application/x-python",
        ]
        
        content = None
        actual_encoding = encoding
        
        if is_text_file and file_size <= 10 * 1024 * 1024:  # 10MB limit for text files
            try:
                with open(target_path, "r", encoding=encoding) as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encodings
                for enc in ["utf-8", "latin-1", "cp1252"]:
                    try:
                        with open(target_path, "r", encoding=enc) as f:
                            content = f.read()
                        actual_encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
                if content is None:
                    content = "[Binary file - cannot display as text]"
                    actual_encoding = None
        
        return FileContentResponse(
            success=True,
            content=content,
            encoding=actual_encoding,
            size=file_size,
            mime_type=mime_type,
            message=f"File content retrieved successfully",
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get file content: {exc}",
        )

@router.get(
    "/download/{file_path:path}",
    summary="Download file",
    description="Download a file from the workspace.",
)
async def download_file(
    file_path: str,
) -> FileResponse:
    """
    Download a file.
    """
    try:
        # Build target path
        target_path = (WORKING_DIR / file_path).resolve()
        
        # Security check
        if not _is_safe_path(WORKING_DIR, target_path):
            raise HTTPException(
                status_code=403,
                detail="Access to this file is not allowed",
            )
        
        # Check if file exists
        if not target_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File does not exist: {file_path}",
            )
        
        # Check if it's a file
        if not target_path.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a file: {file_path}",
            )
        
        return FileResponse(
            path=target_path,
            filename=target_path.name,
            media_type="application/octet-stream",
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download file: {exc}",
        )

@router.delete(
    "/{file_path:path}",
    response_model=FileOperationResponse,
    summary="Delete file or directory",
    description="Delete a file or directory from the workspace.",
)
async def delete_file(
    file_path: str,
) -> FileOperationResponse:
    """
    Delete a file or directory.
    """
    try:
        # Build target path
        target_path = (WORKING_DIR / file_path).resolve()
        
        # Security check
        if not _is_safe_path(WORKING_DIR, target_path):
            raise HTTPException(
                status_code=403,
                detail="Access to this path is not allowed",
            )
        
        # Check if path exists
        if not target_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Path does not exist: {file_path}",
            )
        
        # Delete file or directory
        if target_path.is_file():
            target_path.unlink()
            message = f"File deleted: {file_path}"
        elif target_path.is_dir():
            shutil.rmtree(target_path)
            message = f"Directory deleted: {file_path}"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a file or directory: {file_path}",
            )
        
        return FileOperationResponse(
            success=True,
            message=message,
        )
        
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete: {exc}",
        )

@router.post(
    "/upload",
    response_model=FileOperationResponse,
    summary="Upload file",
    description="Upload a file to the workspace.",
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    path: str = Form("", description="Target directory path relative to WORKING_DIR"),
) -> FileOperationResponse:
    """
    Upload a file.
    """
    try:
        # Build target directory
        if path:
            target_dir = (WORKING_DIR / path).resolve()
        else:
            target_dir = WORKING_DIR.resolve()
        
        # Security check for target directory
        if not _is_safe_path(WORKING_DIR, target_dir):
            raise HTTPException(
                status_code=403,
                detail="Access to this directory is not allowed",
            )
        
        # Check if target directory exists
        if not target_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Target directory does not exist: {path}",
            )
        
        # Check if it's a directory
        if not target_dir.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Target path is not a directory: {path}",
            )
        
        # Build target file path
        target_file = target_dir / file.filename
        
        # Security check for target file
        if not _is_safe_path(WORKING_DIR, target_file):
            raise HTTPException(
                status_code=403,
                detail="Access to this file location is not allowed",
            )
        
        # Check if file already exists
        if target_file.exists():
            raise HTTPException(
                status_code=409,
                detail=f"File already exists: {file.filename}",
            )
        
        # Write file
        with open(target_file, "wb") as f:
            # Read in chunks to handle large files
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)
        
        return FileOperationResponse(
            success=True,
            message=f"File uploaded successfully: {file.filename}",
            data={
                "filename": file.filename,
                "path": str(target_file.relative_to(WORKING_DIR)),
                "size": target_file.stat().st_size,
            },
        )
        
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {exc}",
        )

@router.post(
    "/directory",
    response_model=FileOperationResponse,
    summary="Create directory",
    description="Create a new directory in the workspace.",
)
async def create_directory(
    name: str = Form(..., description="Directory name"),
    path: str = Form("", description="Parent directory path relative to WORKING_DIR"),
) -> FileOperationResponse:
    """
    Create a new directory.
    """
    try:
        # Build parent directory
        if path:
            parent_dir = (WORKING_DIR / path).resolve()
        else:
            parent_dir = WORKING_DIR.resolve()
        
        # Security check for parent directory
        if not _is_safe_path(WORKING_DIR, parent_dir):
            raise HTTPException(
                status_code=403,
                detail="Access to this directory is not allowed",
            )
        
        # Check if parent directory exists
        if not parent_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Parent directory does not exist: {path}",
            )
        
        # Check if parent is a directory
        if not parent_dir.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Parent path is not a directory: {path}",
            )
        
        # Build target directory path
        target_dir = parent_dir / name
        
        # Security check for target directory
        if not _is_safe_path(WORKING_DIR, target_dir):
            raise HTTPException(
                status_code=403,
                detail="Access to this directory location is not allowed",
            )
        
        # Check if directory already exists
        if target_dir.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Directory already exists: {name}",
            )
        
        # Create directory
        target_dir.mkdir(parents=True, exist_ok=False)
        
        return FileOperationResponse(
            success=True,
            message=f"Directory created successfully: {name}",
            data={
                "name": name,
                "path": str(target_dir.relative_to(WORKING_DIR)),
            },
        )
        
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create directory: {exc}",
        )

@router.put(
    "/rename",
    response_model=FileOperationResponse,
    summary="Rename file or directory",
    description="Rename a file or directory in the workspace.",
)
async def rename_file(
    old_path: str = Form(..., description="Old path relative to WORKING_DIR"),
    new_name: str = Form(..., description="New name"),
) -> FileOperationResponse:
    """
    Rename a file or directory.
    """
    try:
        # Build old path
        old_target = (WORKING_DIR / old_path).resolve()
        
        # Security check for old path
        if not _is_safe_path(WORKING_DIR, old_target):
            raise HTTPException(
                status_code=403,
                detail="Access to this path is not allowed",
            )
        
        # Check if old path exists
        if not old_target.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Path does not exist: {old_path}",
            )
        
        # Build new path
        new_target = old_target.parent / new_name
        
        # Security check for new path
        if not _is_safe_path(WORKING_DIR, new_target):
            raise HTTPException(
                status_code=403,
                detail="Access to this new location is not allowed",
            )
        
        # Check if new path already exists
        if new_target.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Target already exists: {new_name}",
            )
        
        # Rename file or directory
        old_target.rename(new_target)
        
        return FileOperationResponse(
            success=True,
            message=f"Renamed successfully: {old_path} -> {new_name}",
            data={
                "old_path": old_path,
                "new_name": new_name,
                "new_path": str(new_target.relative_to(WORKING_DIR)),
            },
        )
        
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rename: {exc}",
        )

@router.get(
    "/stats",
    response_model=FileOperationResponse,
    summary="Get workspace statistics",
    description="Get statistics about the workspace (total size, file count, etc.).",
)
async def get_workspace_stats() -> FileOperationResponse:
    """
    Get workspace statistics.
    """
    try:
        total_size = 0
        file_count = 0
        dir_count = 0
        
        if WORKING_DIR.exists() and WORKING_DIR.is_dir():
            for entry in WORKING_DIR.rglob("*"):
                if entry.is_file():
                    file_count += 1
                    try:
                        total_size += entry.stat().st_size
                    except (PermissionError, OSError):
                        continue
                elif entry.is_dir():
                    dir_count += 1
        
        return FileOperationResponse(
            success=True,
            message="Workspace statistics retrieved successfully",
            data={
                "totalSize": total_size,
                "totalFiles": file_count,
                "dir_count": dir_count,
                "total_items": file_count + dir_count,
                "workspace_path": str(WORKING_DIR),
            },
        )
        
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workspace statistics: {exc}",
        )

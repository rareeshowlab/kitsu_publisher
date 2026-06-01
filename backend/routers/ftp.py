import os
import stat
import json
import asyncio
import logging
import ftplib
import paramiko
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas import FtpConfigModel, FtpBrowseRequest, FtpEntry, FtpTransferRequest, FtpMkdirRequest

router = APIRouter(prefix="/ftp", tags=["ftp"])
logger = logging.getLogger("kitsu_publisher")


def _get_sftp_client(config: FtpConfigModel):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        timeout=15,
        banner_timeout=30,
    )
    return ssh, ssh.open_sftp()


def _get_ftp_client(config: FtpConfigModel):
    ftp = ftplib.FTP()
    ftp.connect(config.host, config.port, timeout=15)
    ftp.login(config.username, config.password)
    ftp.set_pasv(config.passive)
    return ftp


def _sftp_browse(config: FtpConfigModel, path: str) -> List[FtpEntry]:
    ssh, sftp = _get_sftp_client(config)
    try:
        entries = []
        for attr in sorted(sftp.listdir_attr(path), key=lambda a: a.filename):
            if attr.filename.startswith("."):
                continue
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            clean_path = path.rstrip("/") + "/" + attr.filename
            entries.append(FtpEntry(name=attr.filename, path=clean_path, is_dir=is_dir))
        return sorted(entries, key=lambda e: (not e.is_dir, e.name.lower()))
    finally:
        sftp.close()
        ssh.close()


def _ftp_browse(config: FtpConfigModel, path: str) -> List[FtpEntry]:
    ftp = _get_ftp_client(config)
    try:
        entries = []
        try:
            mlsd_entries = list(ftp.mlsd(path))
            for name, facts in mlsd_entries:
                if name in (".", "..") or name.startswith("."):
                    continue
                is_dir = facts.get("type", "").lower() == "dir"
                clean_path = path.rstrip("/") + "/" + name
                entries.append(FtpEntry(name=name, path=clean_path, is_dir=is_dir))
        except ftplib.error_perm:
            # Fallback to LIST if MLSD not supported
            ftp.cwd(path)
            for name in ftp.nlst():
                if name in (".", "..") or name.startswith("."):
                    continue
                try:
                    ftp.cwd(name)
                    ftp.cwd("..")
                    is_dir = True
                except ftplib.error_perm:
                    is_dir = False
                clean_path = path.rstrip("/") + "/" + name
                entries.append(FtpEntry(name=name, path=clean_path, is_dir=is_dir))
        return sorted(entries, key=lambda e: (not e.is_dir, e.name.lower()))
    finally:
        ftp.quit()


def _sftp_upload_file(sftp, local_path: str, remote_path: str):
    remote_dir = remote_path.rsplit("/", 1)[0]
    _sftp_makedirs(sftp, remote_dir)
    sftp.put(local_path, remote_path)


def _sftp_makedirs(sftp, remote_path: str):
    parts = remote_path.lstrip("/").split("/")
    current = ""
    for part in parts:
        current = current + "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def _sftp_upload_folder(sftp, local_folder: str, remote_folder: str):
    _sftp_makedirs(sftp, remote_folder)
    for name in sorted(os.listdir(local_folder)):
        if name.startswith("."):
            continue
        local_item = os.path.join(local_folder, name)
        remote_item = remote_folder.rstrip("/") + "/" + name
        if os.path.isdir(local_item):
            _sftp_upload_folder(sftp, local_item, remote_item)
        else:
            sftp.put(local_item, remote_item)
            logger.info(f"  [SFTP] Uploaded: {name}")


def _ftp_makedirs(ftp: ftplib.FTP, remote_path: str):
    parts = remote_path.lstrip("/").split("/")
    current = ""
    for part in parts:
        current = current + "/" + part
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            ftp.mkd(current)
            ftp.cwd(current)
    ftp.cwd("/")


def _ftp_upload_file(ftp: ftplib.FTP, local_path: str, remote_path: str):
    remote_dir = remote_path.rsplit("/", 1)[0]
    _ftp_makedirs(ftp, remote_dir)
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)


def _ftp_upload_folder(ftp: ftplib.FTP, local_folder: str, remote_folder: str):
    _ftp_makedirs(ftp, remote_folder)
    for name in sorted(os.listdir(local_folder)):
        if name.startswith("."):
            continue
        local_item = os.path.join(local_folder, name)
        remote_item = remote_folder.rstrip("/") + "/" + name
        if os.path.isdir(local_item):
            _ftp_upload_folder(ftp, local_item, remote_item)
        else:
            with open(local_item, "rb") as f:
                ftp.storbinary(f"STOR {remote_item}", f)
            logger.info(f"  [FTP] Uploaded: {name}")


@router.post("/mkdir")
def mkdir_ftp(request: FtpMkdirRequest):
    try:
        if request.config.protocol == "sftp":
            ssh, sftp = _get_sftp_client(request.config)
            try:
                _sftp_makedirs(sftp, request.path)
            finally:
                sftp.close()
                ssh.close()
        else:
            ftp = _get_ftp_client(request.config)
            try:
                _ftp_makedirs(ftp, request.path)
            finally:
                ftp.quit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test")
def test_ftp_connection(config: FtpConfigModel):
    try:
        if config.protocol == "sftp":
            ssh, sftp = _get_sftp_client(config)
            sftp.close()
            ssh.close()
        else:
            ftp = _get_ftp_client(config)
            ftp.quit()
        return {"status": "ok", "message": "Connection successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/browse", response_model=List[FtpEntry])
def browse_ftp(request: FtpBrowseRequest):
    try:
        if request.config.protocol == "sftp":
            return _sftp_browse(request.config, request.path)
        else:
            return _ftp_browse(request.config, request.path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer")
def transfer_files(request: FtpTransferRequest):
    results = []
    try:
        if request.config.protocol == "sftp":
            ssh, sftp = _get_sftp_client(request.config)
            try:
                for item in request.items:
                    remote_path = request.remote_dest.rstrip("/") + "/" + item.remote_name
                    logger.info(f"[FTP] Transferring: {item.remote_name} → {remote_path}")
                    try:
                        if item.is_dir:
                            _sftp_upload_folder(sftp, item.local_path, remote_path)
                        else:
                            _sftp_upload_file(sftp, item.local_path, remote_path)
                        logger.info(f"[FTP] Done: {item.remote_name}")
                        results.append({"local_path": item.local_path, "status": "success"})
                    except Exception as e:
                        logger.error(f"[FTP] Failed: {item.remote_name}: {e}")
                        results.append({"local_path": item.local_path, "status": "error", "message": str(e)})
            finally:
                sftp.close()
                ssh.close()
        else:
            ftp = _get_ftp_client(request.config)
            try:
                for item in request.items:
                    remote_path = request.remote_dest.rstrip("/") + "/" + item.remote_name
                    logger.info(f"[FTP] Transferring: {item.remote_name} → {remote_path}")
                    try:
                        if item.is_dir:
                            _ftp_upload_folder(ftp, item.local_path, remote_path)
                        else:
                            _ftp_upload_file(ftp, item.local_path, remote_path)
                        logger.info(f"[FTP] Done: {item.remote_name}")
                        results.append({"local_path": item.local_path, "status": "success"})
                    except Exception as e:
                        logger.error(f"[FTP] Failed: {item.remote_name}: {e}")
                        results.append({"local_path": item.local_path, "status": "error", "message": str(e)})
            finally:
                ftp.quit()
    except Exception as e:
        logger.error(f"[FTP] Connection error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    return results


# ── 파일 목록 순회 헬퍼 ──────────────────────────────────────────────────────

def _walk_files(folder: str):
    """폴더 내 숨김 파일 제외 모든 파일 경로를 재귀 열거"""
    for name in sorted(os.listdir(folder)):
        if name.startswith("."):
            continue
        path = os.path.join(folder, name)
        if os.path.isdir(path):
            yield from _walk_files(path)
        else:
            yield path


def _count_transferable_files(items) -> int:
    total = 0
    for item in items:
        if item.is_dir:
            total += sum(1 for _ in _walk_files(item.local_path))
        else:
            total += 1
    return total


# ── SSE 스트리밍 전송 엔드포인트 ─────────────────────────────────────────────

@router.post("/transfer-stream")
async def transfer_files_stream(request: FtpTransferRequest):
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(data: dict):
        loop.call_soon_threadsafe(queue.put_nowait, data)

    def do_transfer():
        total_files = _count_transferable_files(request.items)
        uploaded = [0]

        try:
            if request.config.protocol == "sftp":
                ssh, sftp = _get_sftp_client(request.config)
                try:
                    for item in request.items:
                        remote_path = request.remote_dest.rstrip("/") + "/" + item.remote_name
                        emit({"type": "item_start", "local_path": item.local_path, "name": item.remote_name, "group_key": item.group_key})
                        try:
                            if item.is_dir:
                                for fpath in _walk_files(item.local_path):
                                    rel = os.path.relpath(fpath, item.local_path).replace(os.sep, "/")
                                    rpath = remote_path.rstrip("/") + "/" + rel
                                    _sftp_makedirs(sftp, rpath.rsplit("/", 1)[0])
                                    sftp.put(fpath, rpath)
                                    uploaded[0] += 1
                                    emit({"type": "file_done", "name": os.path.basename(fpath), "uploaded": uploaded[0], "total": total_files})
                            else:
                                _sftp_upload_file(sftp, item.local_path, remote_path)
                                uploaded[0] += 1
                                emit({"type": "file_done", "name": item.remote_name, "uploaded": uploaded[0], "total": total_files})
                            emit({"type": "item_done", "local_path": item.local_path, "status": "success", "group_key": item.group_key})
                        except Exception as e:
                            logger.error(f"[SFTP] Failed {item.remote_name}: {e}")
                            emit({"type": "item_done", "local_path": item.local_path, "status": "error", "message": str(e), "group_key": item.group_key})
                finally:
                    sftp.close()
                    ssh.close()
            else:
                ftp = _get_ftp_client(request.config)
                try:
                    for item in request.items:
                        remote_path = request.remote_dest.rstrip("/") + "/" + item.remote_name
                        emit({"type": "item_start", "local_path": item.local_path, "name": item.remote_name, "group_key": item.group_key})
                        try:
                            if item.is_dir:
                                _ftp_makedirs(ftp, remote_path)
                                for fpath in _walk_files(item.local_path):
                                    rel = os.path.relpath(fpath, item.local_path).replace(os.sep, "/")
                                    rpath = remote_path.rstrip("/") + "/" + rel
                                    _ftp_makedirs(ftp, rpath.rsplit("/", 1)[0])
                                    with open(fpath, "rb") as f:
                                        ftp.storbinary(f"STOR {rpath}", f)
                                    uploaded[0] += 1
                                    emit({"type": "file_done", "name": os.path.basename(fpath), "uploaded": uploaded[0], "total": total_files})
                            else:
                                _ftp_upload_file(ftp, item.local_path, remote_path)
                                uploaded[0] += 1
                                emit({"type": "file_done", "name": item.remote_name, "uploaded": uploaded[0], "total": total_files})
                            emit({"type": "item_done", "local_path": item.local_path, "status": "success", "group_key": item.group_key})
                        except Exception as e:
                            logger.error(f"[FTP] Failed {item.remote_name}: {e}")
                            emit({"type": "item_done", "local_path": item.local_path, "status": "error", "message": str(e), "group_key": item.group_key})
                finally:
                    ftp.quit()
            emit({"type": "done"})
        except Exception as e:
            logger.error(f"[FTP] Connection error: {e}")
            emit({"type": "error", "message": str(e)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    async def generate():
        task = loop.run_in_executor(None, do_transfer)
        while True:
            item = await queue.get()
            if item is None:
                await task
                return
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

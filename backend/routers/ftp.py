import os
import stat
import logging
import ftplib
import paramiko
from typing import List
from fastapi import APIRouter, HTTPException

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

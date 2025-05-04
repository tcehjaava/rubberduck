import logging
from functools import wraps
from typing import Optional

from sqlalchemy import Column, ForeignKey, String, Text, create_engine, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from rubberduck.langgraph.graph_orchestrator.tools.repo_context.models import (
    ContentStatus,
    DirectoryTree,
    EntryType,
)

Base = declarative_base()


class FileSystemEntryORM(Base):
    __tablename__ = "file_system_entries"

    id = Column(String, primary_key=True)
    repo = Column(String, index=True)
    commit = Column(String, index=True)
    path = Column(String, nullable=False)
    entry_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    content_status = Column(String, default=ContentStatus.NONE.value)
    parent_id = Column(String, ForeignKey("file_system_entries.id"), nullable=True, index=True)

    children = relationship("FileSystemEntryORM", backref="parent", remote_side=[id])


engine = create_engine("sqlite:///repo_files.db", connect_args={"check_same_thread": False}, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def with_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with Session() as session:
            try:
                result = func(session, *args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                logging.error(f"Error in '{func.__name__}': {e}")
                raise

    return wrapper


class StorageManager:
    @staticmethod
    @with_session
    def store_entry(
        session,
        repo: str,
        commit: str,
        path: str,
        entry_type: EntryType,
        content: Optional[str] = None,
        content_status: Optional[ContentStatus] = None,
        parent_id: Optional[str] = None,
    ):
        entry_id = f"{repo}:{commit}:{path}"
        existing = session.query(FileSystemEntryORM).filter_by(id=entry_id).first()

        if existing:
            if content is not None:
                existing.content = content
            if content_status is not None:
                existing.content_status = content_status.value
            if parent_id is not None:
                existing.parent_id = parent_id
        else:
            entry = FileSystemEntryORM(
                id=entry_id,
                repo=repo,
                commit=commit,
                path=path,
                entry_type=entry_type.value,
                content=content,
                content_status=content_status.value if content_status else ContentStatus.NONE.value,
                parent_id=parent_id,
            )
            session.add(entry)

    @staticmethod
    @with_session
    def get_root_entries(session, repo: str, commit: str):
        return session.query(FileSystemEntryORM).filter_by(repo=repo, commit=commit, parent_id=None).all()

    @staticmethod
    @with_session
    def get_files_needing_summaries(session, repo: str, commit: str):
        all_files = (
            session.query(FileSystemEntryORM.path, FileSystemEntryORM.content_status)
            .filter(
                FileSystemEntryORM.repo == repo,
                FileSystemEntryORM.commit == commit,
                FileSystemEntryORM.entry_type == EntryType.FILE.value,
            )
            .all()
        )

        files_needing_summaries = []

        for entry in all_files:
            if (
                not entry.content_status
                or entry.content_status == ContentStatus.NONE.value
                or entry.content_status == ContentStatus.ERROR.value
            ):
                files_needing_summaries.append(entry.path)

        return files_needing_summaries

    @staticmethod
    @with_session
    def reset_file_summaries(session, repo: str, commit: str):
        files = (
            session.query(FileSystemEntryORM)
            .filter(
                FileSystemEntryORM.repo == repo,
                FileSystemEntryORM.commit == commit,
                FileSystemEntryORM.entry_type == EntryType.FILE.value,
            )
            .all()
        )

        for file in files:
            if file.content_status == ContentStatus.LOADED.value:
                file.content_status = ContentStatus.NONE.value
                file.content = None

    @staticmethod
    @with_session
    def build_directory_tree(session, repo: str, commit: str, from_path: str = ""):
        entries = session.query(FileSystemEntryORM).filter_by(repo=repo, commit=commit).all()

        children_map = {}
        for entry in entries:
            if entry.parent_id not in children_map:
                children_map[entry.parent_id] = []
            children_map[entry.parent_id].append(entry)

        def build_tree(parent_id):
            nodes = []
            for entry in children_map.get(parent_id, []):
                entry_type_enum = EntryType(entry.entry_type) if entry.entry_type else EntryType.FILE
                is_directory = entry_type_enum == EntryType.DIRECTORY

                nodes.append(
                    DirectoryTree(
                        path=entry.path,
                        entry_type=entry_type_enum,
                        summary=entry.content,
                        children=build_tree(entry.id) if is_directory else [],
                    )
                )
            return nodes

        return build_tree(f"{repo}:{commit}:{from_path}" if from_path else None)

    @staticmethod
    def format_directory_tree(tree_nodes, indent=0, show_summaries=True):
        if not tree_nodes:
            return ""

        result = []
        for node in tree_nodes:
            prefix = "  " * indent
            is_dir = node.entry_type == EntryType.DIRECTORY
            icon = "📁" if is_dir else "📄"
            line = f"{prefix}{icon} {node.path}"

            if show_summaries and node.summary and not is_dir:
                line += f": {node.summary}"

            result.append(line)

            if is_dir and node.children:
                result.append(StorageManager.format_directory_tree(node.children, indent + 1, show_summaries))

        return "\n".join(result)

# repo_context/storage_manager.py

import logging
from typing import Dict, List, Optional

from sqlalchemy import Column, ForeignKey, String, Text, create_engine, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from repo_context.models import DirectoryTree, EntryType

Base = declarative_base()


class FileSystemEntryORM(Base):
    __tablename__ = "file_system_entries"
    id = Column(String, primary_key=True)
    repo = Column(String, index=True)
    commit = Column(String, index=True)
    path = Column(String, nullable=False)
    entry_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    parent_id = Column(String, ForeignKey("file_system_entries.id"), nullable=True)

    children = relationship("FileSystemEntryORM", backref="parent", remote_side=[id])


engine = create_engine("sqlite:///repo_files.db", connect_args={"check_same_thread": False}, pool_pre_ping=True)


@event.listens_for(engine, "connect")
def enable_sqlite_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.close()


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


class StorageManager:

    @staticmethod
    def store_entry(
        repo: str,
        commit: str,
        path: str,
        entry_type: EntryType,
        content: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        session = Session()
        entry_id = f"{repo}:{commit}:{path}"
        try:
            entry = FileSystemEntryORM(
                id=entry_id,
                repo=repo,
                commit=commit,
                path=path,
                entry_type=entry_type.value,
                content=content,
                parent_id=parent_id,
            )
            session.merge(entry)
            session.commit()
        except Exception as e:
            session.rollback()
            logging.error(f"Error storing entry '{path}': {e}")
        finally:
            session.close()

    @staticmethod
    def get_root_entries(repo: str, commit: str) -> List[FileSystemEntryORM]:
        session = Session()
        try:
            return session.query(FileSystemEntryORM).filter_by(repo=repo, commit=commit, parent_id=None).all()
        except Exception as e:
            logging.error(f"Error loading root entries: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def get_children(entry_id: str) -> List[FileSystemEntryORM]:
        session = Session()
        try:
            return session.query(FileSystemEntryORM).filter_by(parent_id=entry_id).all()
        except Exception as e:
            logging.error(f"Error loading children for entry '{entry_id}': {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def store_file_paths(repo: str, commit: str, paths: List[str], parent_id: Optional[str] = None):
        for path in paths:
            StorageManager.store_entry(repo, commit, path, EntryType.FILE, parent_id=parent_id)

    @staticmethod
    def store_snippet(repo: str, commit: str, path: str, snippet: str):
        session = Session()
        entry_id = f"{repo}:{commit}:{path}"
        try:
            entry = session.query(FileSystemEntryORM).filter_by(id=entry_id).first()
            if entry:
                entry.content = snippet
                session.commit()
            else:
                StorageManager.store_entry(repo, commit, path, EntryType.FILE, content=snippet)
        except Exception as e:
            session.rollback()
            logging.error(f"Error storing snippet for '{path}': {e}")
        finally:
            session.close()

    @staticmethod
    def store_summary(repo: str, commit: str, path: str, summary: str):
        session = Session()
        entry_id = f"{repo}:{commit}:{path}"
        try:
            entry = session.query(FileSystemEntryORM).filter_by(id=entry_id).first()
            if entry:
                entry.content = summary
                session.commit()
            else:
                StorageManager.store_entry(repo, commit, path, EntryType.FILE, content=summary)
        except Exception as e:
            session.rollback()
            logging.error(f"Error storing summary for '{path}': {e}")
        finally:
            session.close()

    @staticmethod
    def load_summaries(repo: str, commit: str) -> Dict[str, str]:
        session = Session()
        try:
            entries = (
                session.query(FileSystemEntryORM)
                .filter_by(repo=repo, commit=commit, entry_type=EntryType.FILE.value)
                .all()
            )
            return {e.path: e.content for e in entries if e.content}
        except Exception as e:
            logging.error(f"Error loading summaries: {e}")
            return {}
        finally:
            session.close()

    @staticmethod
    def load_file_paths(repo: str, commit: str) -> List[str]:
        session = Session()
        try:
            entries = (
                session.query(FileSystemEntryORM)
                .filter_by(repo=repo, commit=commit, entry_type=EntryType.FILE.value)
                .all()
            )
            return [e.path for e in entries]
        except Exception as e:
            logging.error(f"Error loading file paths: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def load_directory_paths(repo: str, commit: str) -> List[str]:
        session = Session()
        try:
            entries = (
                session.query(FileSystemEntryORM)
                .filter_by(repo=repo, commit=commit, entry_type=EntryType.DIRECTORY.value)
                .all()
            )
            return [e.path for e in entries]
        except Exception as e:
            logging.error(f"Error loading directory paths: {e}")
            return []
        finally:
            session.close()

    @staticmethod
    def load_snippet(repo: str, commit: str, path: str) -> Optional[str]:
        session = Session()
        try:
            entry_id = f"{repo}:{commit}:{path}"
            entry = session.query(FileSystemEntryORM).filter_by(id=entry_id).first()
            return entry.content if entry else None
        except Exception as e:
            logging.error(f"Error loading snippet: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def build_directory_tree(repo: str, commit: str, from_path: str = "") -> Optional[Dict]:
        session = Session()
        try:
            # Get the entry for the specified path
            if from_path:
                entry_id = f"{repo}:{commit}:{from_path}"
                entry = session.query(FileSystemEntryORM).filter_by(id=entry_id).first()
                if not entry:
                    return None
                root_entries = [entry]
            else:
                # Get root entries if no path specified
                root_entries = (
                    session.query(FileSystemEntryORM).filter_by(repo=repo, commit=commit, parent_id=None).all()
                )

            # Build tree recursively
            def build_tree(entries):
                result = []
                for entry in entries:
                    if entry.entry_type == EntryType.DIRECTORY.value:
                        children = session.query(FileSystemEntryORM).filter_by(parent_id=entry.id).all()
                        child_trees = build_tree(children)
                        tree = DirectoryTree(
                            path=entry.path, entry_type=EntryType.DIRECTORY, children=child_trees, summary=entry.content
                        )
                    else:
                        tree = DirectoryTree(
                            path=entry.path, entry_type=EntryType.FILE, children=[], summary=entry.content
                        )
                    result.append(tree)
                return result

            return build_tree(root_entries)

        except Exception as e:
            logging.error(f"Error building directory tree: {e}")
            return None
        finally:
            session.close()

    @staticmethod
    def format_directory_tree(tree_nodes, indent=0, show_summaries=True) -> str:
        if not tree_nodes:
            return ""

        result = []
        for node in tree_nodes:
            prefix = "  " * indent
            is_dir = node.entry_type == EntryType.DIRECTORY
            icon = "📁" if is_dir else "📄"
            line = f"{prefix}{icon} {node.path}"

            # Add summary if available and requested
            if show_summaries and node.summary and not is_dir:
                line += f": {node.summary}"

            result.append(line)

            if is_dir and node.children:
                result.append(StorageManager.format_directory_tree(node.children, indent + 1, show_summaries))

        return "\n".join(result)

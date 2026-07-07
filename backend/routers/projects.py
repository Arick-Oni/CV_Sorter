from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CV, Project
from ..schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.name).all()


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Project name cannot be empty")

    existing = db.query(Project).filter(Project.name == name).first()
    if existing:
        return existing

    project = Project(name=name)
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Project).filter(Project.name == name).first()
        if existing:
            return existing
        raise
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    # Unassign rather than cascade-delete CVs — they stay visible in the global view.
    db.query(CV).filter(CV.project_id == project_id).update({"project_id": None})
    db.delete(project)
    db.commit()

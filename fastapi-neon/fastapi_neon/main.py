# fastapi_neon/main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from fastapi_neon import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException


class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)

# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# The first part of the function, before the yield, will
# be executed before the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan, title="Todo API with DB by Shan Ul Haq", 
    version="0.0.1",)


def get_session():
    with Session(engine) as session:
        yield session


# simple get request to test
@app.get("/")
def read_root():
    return {"Its working properly"}


# read all todos from the database
@app.get("/todos/", response_model=list[Todo])
def read_todos(session: Annotated[Session, Depends(get_session)]):
        todos = session.exec(select(Todo)).all()
        return todos


# create a todo in the database and return it
@app.post("/todos/", response_model=Todo)
def create_todo(todo: Todo, session: Annotated[Session, Depends(get_session)]):
    # with Session(engine) as session:
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo


# update a todo in the database and return it
@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo: Todo, session: Annotated[Session, Depends(get_session)]):
    todo_query = session.exec(select(Todo).where(Todo.id == todo_id)).first()
    if not todo_query:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo_query.content = todo.content
    session.commit()
    session.refresh(todo_query)
    return todo_query


# delete a todo from the database and return it
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, session: Annotated[Session, Depends(get_session)]):
    todo_query = session.exec(select(Todo).where(Todo.id == todo_id)).first()
    if not todo_query:
        raise HTTPException(status_code=404, detail="Todo not found")
    session.delete(todo_query)
    session.commit()
    return {"todo successfully deleted"}


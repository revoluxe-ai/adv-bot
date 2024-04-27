from pydantic import BaseModel


class Subcategory(BaseModel):

    """subjectID
integer
Идентификатор предмета

parentID
integer
Идентификатор родительской категории

subjectName
string
Название предмета

parentName
string
Название родительской категории

isVisible
boolean
Видимость на сайте"""
    subjectID: int
    parentID: int
    subjectName: str
    parentName: str
    isVisible: bool





import factory

from apps.accounts.tests.factories import UserFactory
from apps.courses.models import (
    Assignment,
    Category,
    Chapter,
    ContentItem,
    Course,
    Enrollment,
    Lesson,
    Module,
)


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    kind = "subject"


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    title = factory.Sequence(lambda n: f"Course {n}")
    description = "About the course"
    instructor = factory.SubFactory(UserFactory, role="faculty")
    status = Course.Status.PUBLISHED
    enrollment_mode = Course.EnrollmentMode.OPEN


class ModuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Module

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Module {n}")
    order = factory.Sequence(lambda n: n)


class ChapterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chapter

    module = factory.SubFactory(ModuleFactory)
    title = factory.Sequence(lambda n: f"Chapter {n}")
    order = factory.Sequence(lambda n: n)


class LessonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lesson

    chapter = factory.SubFactory(ChapterFactory)
    title = factory.Sequence(lambda n: f"Lesson {n}")
    order = factory.Sequence(lambda n: n)


class ContentItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentItem

    lesson = factory.SubFactory(LessonFactory)
    kind = ContentItem.Kind.TEXT
    title = "Notes"
    text = "Body"
    order = factory.Sequence(lambda n: n)


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    course = factory.SubFactory(CourseFactory)
    student = factory.SubFactory(UserFactory, role="student")


class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assignment

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Assignment {n}")
    description = "Do the work"
    max_marks = 10
    created_by = factory.LazyAttribute(lambda o: o.course.instructor)

from django.contrib import admin

from quizzes.models import AnswerOption, Question, Quiz


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("order", "text", "points")
    ordering = ("order",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "topic",
        "owner",
        "difficulty",
        "status",
        "created_at",
    )
    list_filter = ("difficulty", "status")
    search_fields = ("title", "description", "owner__username", "owner__email")
    raw_id_fields = ("owner", "source_document")
    readonly_fields = ("created_at", "updated_at")
    inlines = (QuestionInline,)


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0
    fields = ("order", "text", "is_correct")
    ordering = ("order",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "order", "points", "generation_attempts", "text")
    search_fields = ("text", "quiz__title")
    raw_id_fields = ("quiz",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (AnswerOptionInline,)


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "order", "is_correct", "text")
    list_filter = ("is_correct",)
    search_fields = ("text", "question__text", "question__quiz__title")
    raw_id_fields = ("question",)
    readonly_fields = ("created_at", "updated_at")

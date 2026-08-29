from django.contrib import admin

from games.models import SoloAnswer, SoloAttempt


class SoloAnswerInline(admin.TabularInline):
    model = SoloAnswer
    extra = 0
    readonly_fields = ("question", "selected_option", "is_correct", "awarded_points")


@admin.register(SoloAttempt)
class SoloAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "quiz", "status", "score", "max_score", "started_at")
    list_filter = ("status",)
    search_fields = ("user__username", "quiz__title")
    raw_id_fields = ("user", "quiz")
    readonly_fields = ("started_at", "completed_at")
    inlines = (SoloAnswerInline,)


@admin.register(SoloAnswer)
class SoloAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "is_correct", "awarded_points")
    list_filter = ("is_correct",)
    raw_id_fields = ("attempt", "question", "selected_option")
    readonly_fields = ("answered_at",)

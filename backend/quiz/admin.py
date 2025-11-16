from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import json
import traceback

from .models import (
    Subject, Topic, Subskill, Question, Choice, Measure,
    Misconception, StudentResult, PastQuestion, PDFDocument, PDFProcessingLog
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    ordering = ('code',)


class SubskillInline(admin.TabularInline):
    model = Subskill
    extra = 1


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'phase')
    list_filter = ('phase', 'subject')
    search_fields = ('name', 'subject__name')
    inlines = [SubskillInline]
    ordering = ('subject', 'name')


@admin.register(Subskill)
class SubskillAdmin(admin.ModelAdmin):
    list_display = ('name', 'topic', 'subject')
    list_filter = ('topic__subject', 'topic__phase')
    search_fields = ('name', 'topic__name')

    def subject(self, obj):
        return obj.topic.subject.name
    subject.short_description = 'Ders'


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 5
    min_num = 5
    max_num = 5


class MeasureInline(admin.TabularInline):
    model = Measure
    extra = 1


class MisconceptionInline(admin.TabularInline):
    model = Misconception
    extra = 5


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'topic', 'difficulty', 'cognitive', 'created_at')
    list_filter = ('difficulty', 'cognitive', 'subject', 'topic__phase')
    search_fields = ('id', 'question_text', 'topic__name')
    inlines = [ChoiceInline, MeasureInline, MisconceptionInline]
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('id', 'subject', 'topic', 'subskills')
        }),
        ('Soru İçeriği', {
            'fields': ('question_text', 'difficulty', 'cognitive', 'correct_answer', 'explanation')
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(PastQuestion)
class PastQuestionAdmin(admin.ModelAdmin):
    list_display = ('year', 'exam', 'subject', 'topic', 'difficulty', 'cognitive_level')
    list_filter = ('year', 'exam', 'subject', 'difficulty')
    search_fields = ('year', 'subject__code', 'topic__name', 'question_text')
    ordering = ('-year', 'exam', 'subject')


class PDFProcessingLogInline(admin.TabularInline):
    model = PDFProcessingLog
    extra = 0
    readonly_fields = ('started_at', 'completed_at', 'status', 'message')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'subject', 'exam_type', 'year',
                   'is_processed', 'file_size_display', 'created_at')
    list_filter = ('document_type', 'exam_type', 'subject', 'is_processed', 'year')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'processed_at', 'file_size_display')
    inlines = [PDFProcessingLogInline]
    actions = ['process_selected_pdfs']

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'description', 'document_type', 'file')
        }),
        ('Sınav Bilgileri', {
            'fields': ('subject', 'exam_type', 'year'),
            'description': 'Sadece geçmiş sınav PDF\'leri için zorunludur.'
        }),
        ('İşleme Durumu', {
            'fields': ('is_processed', 'processed_at', 'file_size_display'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def file_size_display(self, obj):
        if obj.file:
            size_mb = round(obj.file.size / (1024 * 1024), 2)
            color = 'green' if size_mb < 5 else 'orange' if size_mb < 10 else 'red'
            return format_html('<span style="color: {};">{} MB</span>', color, size_mb)
        return '-'
    file_size_display.short_description = 'Dosya Boyutu'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pdf_id>/process/', self.admin_site.admin_view(self.process_single_pdf),
                 name='process_pdf'),
            path('process-all/', self.admin_site.admin_view(self.process_all_unprocessed),
                 name='process_all_pdfs'),
        ]
        return custom_urls + urls

    def process_selected_pdfs(self, request, queryset):
        """Admin action: seçili PDF'leri işle"""
        success_count = 0
        error_count = 0

        for pdf_obj in queryset:
            if pdf_obj.is_processed:
                continue

            try:
                # İşleme log'u oluştur
                log = PDFProcessingLog.objects.create(
                    pdf_document=pdf_obj,
                    status="PROCESSING",
                    message="Admin tarafından toplu işlem başlatıldı."
                )

                # PDF'i işle
                success = self._process_single_pdf(pdf_obj, log)

                if success:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                PDFProcessingLog.objects.create(
                    pdf_document=pdf_obj,
                    status="FAILED",
                    message=f"Toplu işlem hatası: {str(e)}",
                    error_details={"traceback": traceback.format_exc()}
                )

        if success_count > 0:
            messages.success(request, f'Toplam {success_count} PDF başarıyla işlendi.')
        if error_count > 0:
            messages.error(request, f'{error_count} PDF işlenemedi.')

    process_selected_pdfs.short_description = "Seçili PDF'leri işle"

    def process_single_pdf(self, request, pdf_id):
        """Tek bir PDF'i işle"""
        pdf_obj = get_object_or_404(PDFDocument, id=pdf_id)

        if pdf_obj.is_processed:
            messages.warning(request, 'Bu PDF zaten işlenmiş.')
            return HttpResponseRedirect('/admin/quiz/pdfdocument/')

        try:
            log = PDFProcessingLog.objects.create(
                pdf_document=pdf_obj,
                status="PROCESSING",
                message="Manuel işlem başlatıldı."
            )

            success = self._process_single_pdf(pdf_obj, log)

            if success:
                messages.success(request, f'{pdf_obj.title} başarıyla işlendi.')
            else:
                messages.error(request, f'{pdf_obj.title} işlenirken hata oluştu.')

        except Exception as e:
            messages.error(request, f'Kritik hata: {str(e)}')

        return HttpResponseRedirect('/admin/quiz/pdfdocument/')

    def process_all_unprocessed(self, request):
        """Tüm işlenmemiş PDF'leri işle"""
        pdfs = PDFDocument.objects.filter(is_processed=False)

        if not pdfs.exists():
            messages.info(request, 'İşlenecek bekleyen PDF bulunamadı.')
            return HttpResponseRedirect('/admin/quiz/pdfdocument/')

        count = pdfs.count()
        success_count = 0
        error_count = 0

        for pdf_obj in pdfs:
            try:
                log = PDFProcessingLog.objects.create(
                    pdf_document=pdf_obj,
                    status="PROCESSING",
                    message="Toplu işlem başlatıldı."
                )

                success = self._process_single_pdf(pdf_obj, log)

                if success:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                PDFProcessingLog.objects.create(
                    pdf_document=pdf_obj,
                    status="FAILED",
                    message=f"Toplu işlem hatası: {str(e)}",
                    error_details={"traceback": traceback.format_exc()}
                )

        messages.success(request, f'{count} PDF\'den {success_count} tanesi başarıyla işlendi, {error_count} tanesi hata verdi.')
        return HttpResponseRedirect('/admin/quiz/pdfdocument/')

    def _process_single_pdf(self, pdf_obj, log):
        """Tek bir PDF'i embedding işlemine tabi tutar"""
        try:
            from .pdf_processor import process_pdf_document

            # PDF'i işle
            result = process_pdf_document(pdf_obj)

            if result['success']:
                pdf_obj.is_processed = True
                pdf_obj.processed_at = timezone.now()
                pdf_obj.save()

                log.status = "COMPLETED"
                log.message = result['message']
                log.completed_at = timezone.now()
                log.save()

                return True
            else:
                log.status = "FAILED"
                log.message = result['message']
                log.error_details = result.get('errors', {})
                log.completed_at = timezone.now()
                log.save()

                return False

        except Exception as e:
            log.status = "FAILED"
            log.message = f"Kritik hata: {str(e)}"
            log.error_details = {"traceback": traceback.format_exc()}
            log.completed_at = timezone.now()
            log.save()

            return False


@admin.register(PDFProcessingLog)
class PDFProcessingLogAdmin(admin.ModelAdmin):
    list_display = ('pdf_document', 'status', 'message', 'started_at', 'completed_at')
    list_filter = ('status', 'pdf_document__document_type')
    search_fields = ('pdf_document__title', 'message')
    readonly_fields = ('pdf_document', 'status', 'message', 'error_details',
                      'started_at', 'completed_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Diğer modeller için basit admin kayıtları
admin.site.register(StudentResult)
admin.site.register(Misconception)
admin.site.register(Measure)
admin.site.register(Choice)

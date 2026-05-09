"""
Modelos partilhados a todas as apps.

Aqui vive o `SoftDeleteMixin` (Sprint 4) — uma forma de marcar registos como
apagados sem perder o histórico. A retenção fiscal belga exige 7-10 anos
em documentos contabilísticos: um `DELETE` físico em `Client`/`Invoice`/etc.
viola essa exigência. Marcamos `is_deleted=True` em vez disso.

Como usar num modelo:

    from core.models import SoftDeleteMixin

    class Client(SoftDeleteMixin, models.Model):
        ...

    # Por defeito (Client.objects) só devolve registos vivos.
    # Para incluir apagados:
    Client.all_objects.all()
    # Para listar só apagados:
    Client.all_objects.filter(is_deleted=True)

    cli.delete()                 # soft (default)
    cli.delete(hard=True)        # físico — apenas em scripts de purge
    cli.restore()                # desfaz o soft delete
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet que sabe fazer soft delete em massa e restaurar."""

    def delete(self, hard: bool = False):
        if hard:
            return super().delete()
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager default — só devolve registos vivos."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager que devolve TUDO, incluindo apagados. Usar com parcimónia."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False, editable=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, editable=False,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard: bool = False, user=None):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user is not None and getattr(user, 'pk', None):
            self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

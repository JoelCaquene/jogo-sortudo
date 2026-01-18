from django.contrib import admin
from django.db.models import Sum
from django.utils.timezone import now
from django.utils.html import format_html
from .models import (Usuario, Deposito, Saque, Aposta, Rodada, 
                     ConfiguracaoSistema, MetodoBanco, MetodoExpress, MetodoReferencia)

@admin.register(MetodoBanco)
class MetodoBancoAdmin(admin.ModelAdmin):
    list_display = ('nome_banco', 'titular', 'iban', 'ativo')
    list_editable = ('ativo',)

@admin.register(MetodoExpress)
class MetodoExpressAdmin(admin.ModelAdmin):
    list_display = ('nome_servico', 'numero_telefone', 'ativo')
    list_editable = ('ativo',)

@admin.register(MetodoReferencia)
class MetodoReferenciaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'entidade', 'referencia', 'ativo')
    list_editable = ('ativo',)

@admin.register(ConfiguracaoSistema)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ('link_whatsapp', 'valores_pre_definidos')

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('telefone', 'saldo', 'convidado_por', 'pais')
    search_fields = ('telefone',)

@admin.register(Deposito)
class DepositoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'valor', 'metodo', 'status', 'data_criacao')
    list_filter = ('status', 'metodo')
    actions = ['aprovar_deposito']

    @admin.action(description="Aprovar Depósitos Selecionados")
    def aprovar_deposito(self, request, queryset):
        count = 0
        for deposito in queryset.filter(status='PENDENTE'):
            deposito.status = 'APROVADO'
            deposito.save() 
            count += 1
        self.message_user(request, f"{count} depósitos aprovados.")

@admin.register(Aposta)
class ApostaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rodada', 'valor_investido', 'valor_escolhido', 'ganhou')
    list_filter = ('ganhou', 'rodada')
    
    def changelist_view(self, request, extra_context=None):
        entradas = Aposta.objects.aggregate(Sum('valor_investido'))['valor_investido__sum'] or 0
        extra_context = extra_context or {}
        extra_context['total_entradas'] = entradas
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Rodada)
class RodadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_sorteado', 'ativa', 'data_inicio')

@admin.register(Saque)
class SaqueAdmin(admin.ModelAdmin):
    # 'dados_para_pagamento' aparecerá na sua lista de saques
    list_display = ('usuario', 'valor', 'dados_para_pagamento', 'status', 'data_pedido')
    list_filter = ('status',)
    list_editable = ('status',)
    search_fields = ('usuario__telefone',)

    def dados_para_pagamento(self, obj):
        """
        Esta lógica busca nos seus modelos de Métodos o que enviar para o admin.
        Como o Saque não salva o IBAN, buscamos os métodos ATIVOS do sistema.
        """
        # 1. Tenta buscar dados de Banco ativos
        banco = MetodoBanco.objects.filter(ativo=True).first()
        if banco:
            return format_html(
                '<b style="color: #2e7d32;">🏦 BANCO:</b> {}<br>'
                '<b>Titular:</b> {}<br><b>IBAN:</b> {}',
                banco.nome_banco, banco.titular, banco.iban
            )

        # 2. Se não houver banco ativo, tenta Express
        express = MetodoExpress.objects.filter(ativo=True).first()
        if express:
            return format_html(
                '<b style="color: #1976d2;">📱 EXPRESS:</b> {}',
                express.numero_telefone
            )

        return format_html('<span style="color: red;">Cadastre um método no Admin!</span>')

    dados_para_pagamento.short_description = 'Onde Pagar'
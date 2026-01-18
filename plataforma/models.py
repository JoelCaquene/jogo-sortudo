from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from decimal import Decimal

# --- USUÁRIO ---
class UsuarioManager(BaseUserManager):
    def create_user(self, telefone, password=None, **extra_fields):
        if not telefone: raise ValueError('O telefone é obrigatório')
        user = self.model(telefone=telefone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, telefone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(telefone, password, **extra_fields)

class Usuario(AbstractUser):
    username = None
    telefone = models.CharField(max_length=20, unique=True)
    pais = models.CharField(max_length=50, default='Angola')
    codigo_convite = models.CharField(max_length=10, blank=True)
    convidado_por = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinados')
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    USERNAME_FIELD = 'telefone'
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

# --- MÉTODOS DE PAGAMENTO SEPARADOS (PARA O ADMIN) ---
class MetodoBanco(models.Model):
    nome_banco = models.CharField(max_length=100)
    titular = models.CharField(max_length=100)
    iban = models.CharField(max_length=50)
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.nome_banco

class MetodoExpress(models.Model):
    nome_servico = models.CharField(max_length=100, default="Express")
    numero_telefone = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.numero_telefone

class MetodoReferencia(models.Model):
    empresa = models.CharField(max_length=100)
    entidade = models.CharField(max_length=20)
    referencia = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    def __str__(self): return f"{self.empresa} - {self.entidade}"

# --- FINANCEIRO E JOGO ---
class Deposito(models.Model):
    METODOS = (('BANCO', 'Banco'), ('EXPRESS', 'Express'), ('REFERENCIA', 'Referência'))
    STATUS = (('PENDENTE', 'Pendente'), ('APROVADO', 'Aprovado'), ('REJEITADO', 'Rejeitado'))
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    metodo = models.CharField(max_length=20, choices=METODOS)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    comprovativo = models.ImageField(upload_to='comprovativos/')
    nome_depositante = models.CharField(max_length=100)
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDENTE')

    def save(self, *args, **kwargs):
        if self.pk:
            velho = Deposito.objects.get(pk=self.pk)
            if velho.status == 'PENDENTE' and self.status == 'APROVADO':
                self.usuario.saldo += self.valor
                self.usuario.save()
                if self.usuario.convidado_por:
                    padrinho = self.usuario.convidado_por
                    padrinho.saldo += (self.valor * Decimal('0.15'))
                    padrinho.save()
        super().save(*args, **kwargs)

class Saque(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(2500)])
    status = models.CharField(max_length=20, default='PENDENTE')
    data_pedido = models.DateTimeField(auto_now_add=True)

class Rodada(models.Model):
    numero_sorteado = models.IntegerField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    data_inicio = models.DateTimeField(auto_now_add=True)

class Aposta(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    rodada = models.ForeignKey(Rodada, on_delete=models.CASCADE, related_name='apostas')
    valor_escolhido = models.IntegerField()
    valor_investido = models.DecimalField(max_digits=10, decimal_places=2)
    ganhou = models.BooleanField(null=True, blank=True)
    def __str__(self):
        return f"Aposta de {self.usuario.telefone} - Kz {self.valor_investido}"

class ConfiguracaoSistema(models.Model):
    link_whatsapp = models.URLField()
    instrucoes_jogo = models.TextField()
    valores_pre_definidos = models.CharField(max_length=255, help_text="Ex: 1000, 2000, 5000")
    
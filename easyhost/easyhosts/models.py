from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    TIPOS_USUARIO = [
        ('dono', 'Dono'),
        ('funcionario', 'Funcionário'),
    ]
    tipo = models.CharField(max_length=11, choices=TIPOS_USUARIO)
    
    class Meta:
        db_table = 'usuario'

# models.py
class Hospede(models.Model):
    
    nome_completo = models.CharField(max_length=100)
    telefone = models.CharField(max_length=15)
    cpf = models.CharField(max_length=14, blank=True, null=True, unique=True)
    email = models.EmailField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hospede'
        verbose_name = 'Hóspede'
        verbose_name_plural = 'Hóspedes'

    def __str__(self):
        return self.nome_completo

class Quarto(models.Model):
    TIPOS_QUARTO = [
        ('solteiro', 'Solteiro'),
        ('casal', 'Casal'),
        ('suite', 'Suíte'),
        ('familia', 'Família'),
    ]
    numero_quarto = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPOS_QUARTO)

    class Meta:
        db_table = 'quarto'

    def __str__(self):
        return f"Quarto {self.numero_quarto} ({self.get_tipo_display()})"


#TABELA RESERVA ONDE FAZ O CHECKIN
#CASO QUEIRA FAZER O CHECKOUT O USUARIO PRECISAR CONSULTAR/EDITAR
#O REGISTRO DE CHECK IN ADICIONANDO A DATA DE CHECKOUT
class Reserva(models.Model):
    STATUS_RESERVA = [
        ('pendente', 'Pendente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('concluida', 'Concluída'),
    ]
    quarto = models.ForeignKey(Quarto, on_delete=models.CASCADE)
    hospede = models.ForeignKey(Hospede, on_delete=models.CASCADE)
    data_checkin = models.DateField()
    data_checkout = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_RESERVA, default='confirmada')
    data_reserva = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta: 
        db_table = 'reserva'
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def __str__(self):
        return f"Reserva #{self.id} - {self.hospede.nome_completo}"

class Receita(models.Model):
    TIPOS_RECEITA = [
        ('Diária', 'Diária'),
        ('Frigobar', 'Frigobar'),
        ('Estacionamento', 'Estacionamento'),
        ('Lavanderia', 'Lavanderia'),
        ('Taxa Extra', 'Taxa Extra'),
        ('Outro', 'Outro'),
    ]

    FORMAS_PAGAMENTO = [
        ('Dinheiro', 'Dinheiro'),
        ('Cartão de Crédito', 'Cartão de Crédito'),
        ('Cartão de Débito', 'Cartão de Débito'),
        ('Pix', 'Pix'),
        ('Transferência Bancária', 'Transferência Bancária'),
        ('Boleto', 'Boleto'),
        ('Outros', 'Outros'),
    ]

    data = models.DateField()
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_RECEITA)
    forma_pagamento = models.CharField(max_length=25, choices=FORMAS_PAGAMENTO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    quarto = models.ForeignKey('Quarto', on_delete=models.SET_NULL, null=True, blank=True)  # Opcional

    class Meta:
        db_table = 'receita'
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'

    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} em {self.data}"

class Despesa(models.Model):
    TIPOS_DESPESA = [
        ('Folha de Pagamento', 'Folha de Pagamento'),
        ('Contas', 'Contas (Luz, Água, Internet)'),
        ('Suprimentos e Limpeza', 'Suprimentos e Limpeza'),
        ('Manutenção e Reparos', 'Manutenção e Reparos'),
        ('Impostos e Taxas', 'Impostos e Taxas'),
        ('Equipamentos e Móveis', 'Equipamentos e Móveis'),
        ('Serviços Terceirizados', 'Serviços Terceirizados'),
        ('Deslocamentos e Transporte', 'Deslocamentos e Transporte'),
        ('Multas e Encargos', 'Multas e Encargos'),
        ('Outros', 'Outros'),
    ]

    FORMAS_PAGAMENTO = [
        ('Dinheiro', 'Dinheiro'),
        ('Cartão de Crédito', 'Cartão de Crédito'),
        ('Cartão de Débito', 'Cartão de Débito'),
        ('Pix', 'Pix'),
        ('Transferência Bancária', 'Transferência Bancária'),
        ('Boleto', 'Boleto'),
        ('Outros', 'Outros'),
    ]

    data = models.DateField()
    descricao = models.TextField()
    tipo = models.CharField(max_length=30, choices=TIPOS_DESPESA)
    forma_pagamento = models.CharField(max_length=25, choices=FORMAS_PAGAMENTO)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    responsavel = models.CharField(max_length=100)

    class Meta:
        db_table = 'despesa'
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'

    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} em {self.data}"

class Relatorio(models.Model):
    TIPOS_RELATORIO = [
        ('financeiro', 'Financeiro'),
        ('operacional', 'Operacional'),
        ('hospedes', 'Hóspedes'),
        ('manutencao', 'Manutenção'),
        ('outro', 'Outro'),
    ]
    
    data_criacao = models.DateField()
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_RELATORIO)
    responsavel = models.CharField(max_length=100)
    observacoes = models.TextField(blank=True, null=True)
    arquivo = models.FileField(upload_to='relatorios/', blank=True, null=True)
    
    class Meta:
        db_table = 'relatorio'
        verbose_name = 'Relatório'
        verbose_name_plural = 'Relatórios'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

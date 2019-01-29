# Generated by Django 2.1.5 on 2019-01-25 10:33

from django.db import migrations, models
import django.db.models.deletion
import pkdb_app.storage


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Characteristica',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(blank=True, null=True)),
                ('mean', models.FloatField(blank=True, null=True)),
                ('median', models.FloatField(blank=True, null=True)),
                ('min', models.FloatField(blank=True, null=True)),
                ('max', models.FloatField(blank=True, null=True)),
                ('sd', models.FloatField(blank=True, null=True)),
                ('se', models.FloatField(blank=True, null=True)),
                ('cv', models.FloatField(blank=True, null=True)),
                ('unit', models.CharField(blank=True, choices=[('-', '-'), ('%', '%'), ('mega', 'mega'), ('kilo', 'kilo'), ('milli', 'milli'), ('micro', 'micro'), ('cm', 'cm'), ('m', 'm'), ('kg', 'kg'), ('mg', 'mg'), ('g', 'g'), ('mmHg', 'mmHg'), ('mmol', 'mmol'), ('µmol', 'µmol'), ('nmol', 'nmol'), ('m^2', 'm^2'), ('1/week', '1/week'), ('1/day', '1/day'), ('1/h', '1/h'), ('1/min', '1/min'), ('1/s', '1/s'), ('g/kg', 'g/kg'), ('mg/kg', 'mg/kg'), ('pmol/kg', 'pmol/kg'), ('mg/70kg', 'mg/70kg'), ('mU/kg', 'mU/kg'), ('U/kg', 'U/kg'), ('mg/day', 'mg/day'), ('kg/m^2', 'kg/m^2'), ('IU/I', 'IU/I'), ('µg/l', 'µg/l'), ('µg/ml', 'µg/ml'), ('µg/dl', 'µg/dl'), ('mg/dl', 'mg/dl'), ('mg/100ml', 'mg/100ml'), ('mg/l', 'mg/l'), ('ng/l', 'ng/l'), ('g/dl', 'g/dl'), ('ng/ml', 'ng/ml'), ('pg/ml', 'pg/ml'), ('mmol/l', 'mmol/l'), ('nmol/ml', 'nmol/ml'), ('µmol/l', 'µmol/l'), ('nmol/l', 'nmol/l'), ('pmol/l', 'pmol/l'), ('pmol/ml', 'pmol/ml'), ('fmol/l', 'fmol/l'), ('µU/ml', 'µU/ml'), ('ng/g', 'ng/g'), ('h*mg/l', 'h*mg/l'), ('h*µg/l', 'h*µg/l'), ('h*µg/ml', 'h*µg/ml'), ('mg*h/l', 'mg*h/l'), ('mg/l*h', 'mg/l*h'), ('ng*h/ml', 'ng*h/ml'), ('ng*min/ml', 'ng*min/ml'), ('µg*h/ml', 'µg*h/ml'), ('µg/ml*h', 'µg/ml*h'), ('mg*min/l', 'mg*min/l'), ('mg/l*min', 'mg/l*min'), ('µg*min/ml', 'µg*min/ml'), ('µmol*h/l', 'µmol*h/l'), ('µmol/l*h', 'µmol/l*h'), ('pmol*h/ml', 'pmol*h/ml'), ('pmol/ml*h', 'pmol/ml*h'), ('h*pmol/ml', 'h*pmol/ml'), ('nmol*h/l', 'nmol*h/l'), ('nmol/l*h', 'nmol/l*h'), ('µg/ml*h/kg', 'µg/ml*h/kg'), ('mg*h/l/kg', 'mg*h/l/kg'), ('µU/ml*min', 'µU/ml*min'), ('mg*h^2/l', 'mg*h^2/l'), ('mg/l*h^2', 'mg/l*h^2'), ('ng*h^2/ml', 'ng*h^2/ml'), ('ng*min^2/ml', 'ng*min^2/ml'), ('µg*h^2/ml', 'µg*h^2/ml'), ('µg/ml*h^2', 'µg/ml*h^2'), ('mg*min^2/l', 'mg*min^2/l'), ('mg/l*min^2', 'mg/l*min^2'), ('µg*min^2/ml', 'µg*min^2/ml'), ('µmol*h^2/l', 'µmol*h^2/l'), ('µmol/l*h^2', 'µmol/l*h^2'), ('pmol*h^2/ml', 'pmol*h^2/ml'), ('pmol/ml*h^2', 'pmol/ml*h^2'), ('nmol*h^2/l', 'nmol*h^2/l'), ('µg/ml*h^2/kg', 'µg/ml*h^2/kg'), ('mg*h^2/l/kg', 'mg*h^2/l/kg'), ('µU/ml*min^2', 'µU/ml*min^2'), ('l', 'l'), ('ml', 'ml'), ('l/kg', 'l/kg'), ('ml/kg', 'ml/kg'), ('ml/min', 'ml/min'), ('ml/h', 'ml/h'), ('l/h', 'l/h'), ('l/h/kg', 'l/h/kg'), ('l/h*kg', 'l/h*kg'), ('ml/h/kg', 'ml/h/kg'), ('ml/kg/min', 'ml/kg/min'), ('ml/min/kg', 'ml/min/kg'), ('ml/min/1.73m^2', 'ml/min/1.73m^2'), ('mg/min', 'mg/min'), ('µg/min', 'µg/min'), ('mg/kg/min', 'mg/kg/min'), ('mg/min/kg', 'mg/min/kg'), ('µmol/min', 'µmol/min'), ('µmol/kg/min', 'µmol/kg/min'), ('µmol/min/kg', 'µmol/min/kg'), ('pmol/min', 'pmol/min'), ('pmol/kg/min', 'pmol/kg/min'), ('pmol/min/kg', 'pmol/min/kg'), ('mU/min', 'mU/min'), ('mU/min/kg', 'mU/min/kg'), ('mU/kg/min', 'mU/kg/min'), ('cups/day', 'cups/day'), ('g/day', 'g/day'), ('yr', 'yr'), ('week', 'week'), ('day', 'day'), ('h', 'h'), ('min', 'min'), ('s', 's')], max_length=200, null=True)),
                ('category', models.CharField(choices=[('species', 'species'), ('height', 'height'), ('weight', 'weight'), ('bmi', 'bmi'), ('body surface area', 'body surface area'), ('waist circumference', 'waist circumference'), ('lean body mass', 'lean body mass'), ('percent fat', 'percent fat'), ('obesity index', 'obesity index'), ('obese', 'obese'), ('age', 'age'), ('sex', 'sex'), ('ethnicity', 'ethnicity'), ('blood pressure', 'blood pressure'), ('heart rate', 'heart rate'), ('liver weight', 'liver weight'), ('kidney weight', 'kidney weight'), ('muscle weight', 'muscle weight'), ('fat weight', 'fat weight'), ('overnight fast', 'overnight fast'), ('fasted', 'fasted'), ('healthy', 'healthy'), ('disease', 'disease'), ('disease duration', 'disease duration'), ('medication', 'medication'), ('medication type', 'medication type'), ('medication amount', 'medication amount'), ('oral contraceptives', 'oral contraceptives'), ('abstinence', 'abstinence'), ('consumption', 'consumption'), ('metabolic challenge', 'metabolic challenge'), ('sleeping', 'sleeping'), ('circadian', 'circadian'), ('caffeine', 'caffeine'), ('caffeine amount', 'caffeine amount'), ('caffeine amount (beverages)', 'caffeine amount (beverages)'), ('smoking', 'smoking'), ('smoking amount (cigarettes)', 'smoking amount (cigarettes)'), ('smoking amount (packyears)', 'smoking amount (packyears)'), ('smoking duration (years)', 'smoking duration (years)'), ('alcohol', 'alcohol'), ('alcohol amount', 'alcohol amount'), ('alcohol abstinence', 'alcohol abstinence'), ('ALT', 'ALT'), ('AST', 'AST'), ('albumin', 'albumin'), ('glucose', 'glucose'), ('insulin', 'insulin'), ('glucagon', 'glucagon'), ('cholesterol', 'cholesterol'), ('triglyceride', 'triglyceride'), ('LDL-C', 'LDL-C'), ('LDL-H', 'LDL-H'), ('HbA1c', 'HbA1c'), ('genetics', 'genetics'), ('phenotype', 'phenotype'), ('CYP2D6 genotype', 'CYP2D6 genotype'), ('metabolic ratio', 'metabolic ratio')], max_length=200)),
                ('choice', models.CharField(max_length=600, null=True)),
                ('ctype', models.CharField(choices=[('inclusion', 'inclusion'), ('exclusion', 'exclusion'), ('group', 'group')], default='group', max_length=200)),
                ('final', models.BooleanField(default=False)),
                ('count', models.IntegerField(default=1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CharacteristicaEx',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(null=True)),
                ('mean', models.FloatField(null=True)),
                ('median', models.FloatField(null=True)),
                ('min', models.FloatField(null=True)),
                ('max', models.FloatField(null=True)),
                ('sd', models.FloatField(null=True)),
                ('se', models.FloatField(null=True)),
                ('cv', models.FloatField(null=True)),
                ('unit', models.CharField(choices=[('-', '-'), ('%', '%'), ('mega', 'mega'), ('kilo', 'kilo'), ('milli', 'milli'), ('micro', 'micro'), ('cm', 'cm'), ('m', 'm'), ('kg', 'kg'), ('mg', 'mg'), ('g', 'g'), ('mmHg', 'mmHg'), ('mmol', 'mmol'), ('µmol', 'µmol'), ('nmol', 'nmol'), ('m^2', 'm^2'), ('1/week', '1/week'), ('1/day', '1/day'), ('1/h', '1/h'), ('1/min', '1/min'), ('1/s', '1/s'), ('g/kg', 'g/kg'), ('mg/kg', 'mg/kg'), ('pmol/kg', 'pmol/kg'), ('mg/70kg', 'mg/70kg'), ('mU/kg', 'mU/kg'), ('U/kg', 'U/kg'), ('mg/day', 'mg/day'), ('kg/m^2', 'kg/m^2'), ('IU/I', 'IU/I'), ('µg/l', 'µg/l'), ('µg/ml', 'µg/ml'), ('µg/dl', 'µg/dl'), ('mg/dl', 'mg/dl'), ('mg/100ml', 'mg/100ml'), ('mg/l', 'mg/l'), ('ng/l', 'ng/l'), ('g/dl', 'g/dl'), ('ng/ml', 'ng/ml'), ('pg/ml', 'pg/ml'), ('mmol/l', 'mmol/l'), ('nmol/ml', 'nmol/ml'), ('µmol/l', 'µmol/l'), ('nmol/l', 'nmol/l'), ('pmol/l', 'pmol/l'), ('pmol/ml', 'pmol/ml'), ('fmol/l', 'fmol/l'), ('µU/ml', 'µU/ml'), ('ng/g', 'ng/g'), ('h*mg/l', 'h*mg/l'), ('h*µg/l', 'h*µg/l'), ('h*µg/ml', 'h*µg/ml'), ('mg*h/l', 'mg*h/l'), ('mg/l*h', 'mg/l*h'), ('ng*h/ml', 'ng*h/ml'), ('ng*min/ml', 'ng*min/ml'), ('µg*h/ml', 'µg*h/ml'), ('µg/ml*h', 'µg/ml*h'), ('mg*min/l', 'mg*min/l'), ('mg/l*min', 'mg/l*min'), ('µg*min/ml', 'µg*min/ml'), ('µmol*h/l', 'µmol*h/l'), ('µmol/l*h', 'µmol/l*h'), ('pmol*h/ml', 'pmol*h/ml'), ('pmol/ml*h', 'pmol/ml*h'), ('h*pmol/ml', 'h*pmol/ml'), ('nmol*h/l', 'nmol*h/l'), ('nmol/l*h', 'nmol/l*h'), ('µg/ml*h/kg', 'µg/ml*h/kg'), ('mg*h/l/kg', 'mg*h/l/kg'), ('µU/ml*min', 'µU/ml*min'), ('mg*h^2/l', 'mg*h^2/l'), ('mg/l*h^2', 'mg/l*h^2'), ('ng*h^2/ml', 'ng*h^2/ml'), ('ng*min^2/ml', 'ng*min^2/ml'), ('µg*h^2/ml', 'µg*h^2/ml'), ('µg/ml*h^2', 'µg/ml*h^2'), ('mg*min^2/l', 'mg*min^2/l'), ('mg/l*min^2', 'mg/l*min^2'), ('µg*min^2/ml', 'µg*min^2/ml'), ('µmol*h^2/l', 'µmol*h^2/l'), ('µmol/l*h^2', 'µmol/l*h^2'), ('pmol*h^2/ml', 'pmol*h^2/ml'), ('pmol/ml*h^2', 'pmol/ml*h^2'), ('nmol*h^2/l', 'nmol*h^2/l'), ('µg/ml*h^2/kg', 'µg/ml*h^2/kg'), ('mg*h^2/l/kg', 'mg*h^2/l/kg'), ('µU/ml*min^2', 'µU/ml*min^2'), ('l', 'l'), ('ml', 'ml'), ('l/kg', 'l/kg'), ('ml/kg', 'ml/kg'), ('ml/min', 'ml/min'), ('ml/h', 'ml/h'), ('l/h', 'l/h'), ('l/h/kg', 'l/h/kg'), ('l/h*kg', 'l/h*kg'), ('ml/h/kg', 'ml/h/kg'), ('ml/kg/min', 'ml/kg/min'), ('ml/min/kg', 'ml/min/kg'), ('ml/min/1.73m^2', 'ml/min/1.73m^2'), ('mg/min', 'mg/min'), ('µg/min', 'µg/min'), ('mg/kg/min', 'mg/kg/min'), ('mg/min/kg', 'mg/min/kg'), ('µmol/min', 'µmol/min'), ('µmol/kg/min', 'µmol/kg/min'), ('µmol/min/kg', 'µmol/min/kg'), ('pmol/min', 'pmol/min'), ('pmol/kg/min', 'pmol/kg/min'), ('pmol/min/kg', 'pmol/min/kg'), ('mU/min', 'mU/min'), ('mU/min/kg', 'mU/min/kg'), ('mU/kg/min', 'mU/kg/min'), ('cups/day', 'cups/day'), ('g/day', 'g/day'), ('yr', 'yr'), ('week', 'week'), ('day', 'day'), ('h', 'h'), ('min', 'min'), ('s', 's')], max_length=200, null=True)),
                ('value_map', models.CharField(max_length=600, null=True)),
                ('mean_map', models.CharField(max_length=600, null=True)),
                ('median_map', models.CharField(max_length=600, null=True)),
                ('min_map', models.CharField(max_length=600, null=True)),
                ('max_map', models.CharField(max_length=600, null=True)),
                ('sd_map', models.CharField(max_length=600, null=True)),
                ('se_map', models.CharField(max_length=600, null=True)),
                ('cv_map', models.CharField(max_length=600, null=True)),
                ('unit_map', models.CharField(max_length=600, null=True)),
                ('category', models.CharField(choices=[('species', 'species'), ('height', 'height'), ('weight', 'weight'), ('bmi', 'bmi'), ('body surface area', 'body surface area'), ('waist circumference', 'waist circumference'), ('lean body mass', 'lean body mass'), ('percent fat', 'percent fat'), ('obesity index', 'obesity index'), ('obese', 'obese'), ('age', 'age'), ('sex', 'sex'), ('ethnicity', 'ethnicity'), ('blood pressure', 'blood pressure'), ('heart rate', 'heart rate'), ('liver weight', 'liver weight'), ('kidney weight', 'kidney weight'), ('muscle weight', 'muscle weight'), ('fat weight', 'fat weight'), ('overnight fast', 'overnight fast'), ('fasted', 'fasted'), ('healthy', 'healthy'), ('disease', 'disease'), ('disease duration', 'disease duration'), ('medication', 'medication'), ('medication type', 'medication type'), ('medication amount', 'medication amount'), ('oral contraceptives', 'oral contraceptives'), ('abstinence', 'abstinence'), ('consumption', 'consumption'), ('metabolic challenge', 'metabolic challenge'), ('sleeping', 'sleeping'), ('circadian', 'circadian'), ('caffeine', 'caffeine'), ('caffeine amount', 'caffeine amount'), ('caffeine amount (beverages)', 'caffeine amount (beverages)'), ('smoking', 'smoking'), ('smoking amount (cigarettes)', 'smoking amount (cigarettes)'), ('smoking amount (packyears)', 'smoking amount (packyears)'), ('smoking duration (years)', 'smoking duration (years)'), ('alcohol', 'alcohol'), ('alcohol amount', 'alcohol amount'), ('alcohol abstinence', 'alcohol abstinence'), ('ALT', 'ALT'), ('AST', 'AST'), ('albumin', 'albumin'), ('glucose', 'glucose'), ('insulin', 'insulin'), ('glucagon', 'glucagon'), ('cholesterol', 'cholesterol'), ('triglyceride', 'triglyceride'), ('LDL-C', 'LDL-C'), ('LDL-H', 'LDL-H'), ('HbA1c', 'HbA1c'), ('genetics', 'genetics'), ('phenotype', 'phenotype'), ('CYP2D6 genotype', 'CYP2D6 genotype'), ('metabolic ratio', 'metabolic ratio')], max_length=200)),
                ('choice', models.CharField(max_length=600, null=True)),
                ('ctype', models.CharField(choices=[('inclusion', 'inclusion'), ('exclusion', 'exclusion'), ('group', 'group')], default='group', max_length=200)),
                ('count', models.IntegerField(null=True)),
                ('count_map', models.CharField(max_length=200, null=True)),
                ('choice_map', models.CharField(max_length=200, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DataFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(blank=True, null=True, storage=pkdb_app.storage.OverwriteStorage(), upload_to='data')),
                ('filetype', models.CharField(blank=True, max_length=200, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('count', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='GroupEx',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('format', models.CharField(max_length=200, null=True)),
                ('subset_map', models.CharField(max_length=600, null=True)),
                ('groupby', models.CharField(max_length=600, null=True)),
                ('name', models.CharField(max_length=200)),
                ('name_map', models.CharField(max_length=200, null=True)),
                ('count', models.IntegerField()),
                ('count_map', models.CharField(max_length=200, null=True)),
                ('figure', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='f_group_exs', to='subjects.DataFile')),
            ],
        ),
        migrations.CreateModel(
            name='GroupSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IndividualEx',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subset_map', models.CharField(max_length=600, null=True)),
                ('groupby', models.CharField(max_length=600, null=True)),
                ('format', models.CharField(blank=True, max_length=200, null=True)),
                ('group_map', models.CharField(max_length=200, null=True)),
                ('name', models.CharField(max_length=200, null=True)),
                ('name_map', models.CharField(max_length=200, null=True)),
                ('figure', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='f_individual_exs', to='subjects.DataFile')),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='individual_exs', to='subjects.Group')),
            ],
        ),
        migrations.CreateModel(
            name='IndividualSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.AddField(
            model_name='individualex',
            name='individualset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='individual_exs', to='subjects.IndividualSet'),
        ),
        migrations.AddField(
            model_name='individualex',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='s_individual_exs', to='subjects.DataFile'),
        ),
        migrations.AddField(
            model_name='individual',
            name='ex',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='individuals', to='subjects.IndividualEx'),
        ),
        migrations.AddField(
            model_name='individual',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='individuals', to='subjects.Group'),
        ),
        migrations.AddField(
            model_name='groupex',
            name='groupset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group_exs', to='subjects.GroupSet'),
        ),
        migrations.AddField(
            model_name='groupex',
            name='parent_ex',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='subjects.GroupEx'),
        ),
        migrations.AddField(
            model_name='groupex',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='s_group_exs', to='subjects.DataFile'),
        ),
        migrations.AddField(
            model_name='group',
            name='ex',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='subjects.GroupEx'),
        ),
        migrations.AddField(
            model_name='group',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='subjects.Group'),
        ),
        migrations.AddField(
            model_name='characteristicaex',
            name='group_ex',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='characteristica_ex', to='subjects.GroupEx'),
        ),
        migrations.AddField(
            model_name='characteristicaex',
            name='individual_ex',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='characteristica_ex', to='subjects.IndividualEx'),
        ),
        migrations.AddField(
            model_name='characteristica',
            name='group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='characteristica', to='subjects.Group'),
        ),
        migrations.AddField(
            model_name='characteristica',
            name='individual',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='characteristica', to='subjects.Individual'),
        ),
        migrations.AddField(
            model_name='characteristica',
            name='raw',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='norm', to='subjects.Characteristica'),
        ),
        migrations.AlterUniqueTogether(
            name='individualex',
            unique_together={('individualset', 'name', 'name_map', 'source')},
        ),
        migrations.AlterUniqueTogether(
            name='groupex',
            unique_together={('groupset', 'name', 'name_map', 'source')},
        ),
    ]
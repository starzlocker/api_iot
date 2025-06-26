import frappe
from frappe import utils
import json
from nxlite.nx_producao.page.apontamento_iot.charts.disp_resumida import DispResumida
from nxlite.nx_producao.page.apontamento_iot.charts.paretoParadas import ParetoParadas
from nxlite.nx_producao.page.apontamento_iot.charts.desempenho import Desempenho
from nxlite.nx_producao.page.apontamento_iot.charts.maquinasSatus import MaquinaStatus


from nxlite.nx_producao.page.apontamento_iot.charts_iot import ChartsIot
from nxlite.nx_producao.page.apontamento_iot.configIOT import ConfigIot

from functools import reduce
from datetime import time, datetime, date, timedelta

import frappe.utils
from frappe.utils import add_days, date_diff, time_diff_in_seconds,time_diff_in_hours
import traceback
import paho.mqtt.publish as publish

dias_da_semana = ['disponibilidade_segunda_feira',
                               'disponibilidade_terca_feira',
                               'disponibilidade_quarta_feira',
                               'disponibilidade_quinta_feira',
                               'disponibilidade_sexta_feira',
                               'disponibilidade_sabado',
                               'disponibilidade_domingo']


@frappe.whitelist()
def publish_to_mqtt_get(serial):
        try:
            _username = frappe.get_conf().get(
                "events", "xZuJRXQ4Zqhe9C6PefcDRZXuLBeYmZ22FwKpQeww")
            
            _password = frappe.get_conf().get(
                "events", "xZuJRXQ4Zqhe9C6PefcDRZXuLBeYmZ22FwKpQeww")
                
            _port = 1883
            
            mqtt_broker = "s1.apontafacil.com"  
            mqtt_topic = f"/NX/NXS/{serial}/GET"
            mqtt_payload = 'TUDO'

            auth = {'username': _username, 'password': _password}

            publish.single(mqtt_topic, mqtt_payload, hostname=mqtt_broker, port=_port, auth=auth)
        except Exception as e:
            print('error publish_to_mqtt',str(e))

@frappe.whitelist()
def setup_teste_automatizado():
    try:     
        frappe.db.sql("delete from tabRecurso")
        frappe.db.commit()

        frappe.db.sql("delete from tabApontamento")
        frappe.db.commit()

        frappe.db.sql("delete from tabdisponibilidade_turno_apontamento")
        frappe.db.commit()
        
    except Exception as e:
        print('error setup_teste_automatizado',str(e))

@frappe.whitelist()
def format_qry(value=[]):
        if not value:  # Se a lista estiver vazia, retorna NULL
            return "NULL"
        return ','.join(f"'{v}'" for v in value)  # Gera 'REC00003', 'REC00002'

@frappe.whitelist()
def filter_front(filters={}):
    try:
        filtros = filters
        filtro_ajustado = {}

        if 'recurso' in filtros:
            filtro_ajustado['recurso'] = filtros["recurso"]

        if 'dt_inicio' in filtros and 'dt_fim' in filtros: 
            _data_inicio = datetime.strptime(filtros['dt_inicio'], "%d/%m/%Y").date()
            _dt_inicio_iso = _data_inicio.isoformat()
        
            _data_fim = datetime.strptime(filtros['dt_fim'], "%d/%m/%Y").date()
            _dt_fim_iso = _data_fim.isoformat()

            filtro_ajustado['dt_inicio'] =  _dt_inicio_iso

            filtro_ajustado['dt_fim'] = _dt_fim_iso

        return filtro_ajustado

    except Exception as e:
        print('error filter_front',str(e))



@frappe.whitelist()
def disponibilidade_atual(recurso, turno):
    try:
        if turno:
            dt_init = utils.now_datetime().date()
                        
            disp_turno = f'{recurso}-{turno}: {dt_init}'

            percentual_producao = frappe.db.get_value(
                        'Disponibilidade por turno', disp_turno, 'percentual_producao') 
            
            percentual_setup = frappe.db.get_value(
                        'Disponibilidade por turno', disp_turno, 'percentual_setup') 
            
            _percent = 0

            if percentual_producao:
                _percent += round(percentual_producao, 2)
            if percentual_setup:
                _percent += round(percentual_setup, 2)
                
            return _percent
        return 0
    except Exception as e:
        print('error disponibilidade_atual',str(e))
        return 0

@frappe.whitelist()
def get_all_apontamentos_abertos():
    apontamentos = frappe.db.get_all(
        'Apontamento', filters={'status': 'Aberto'}, fields="*")
    if not apontamentos:
        return {'producao': [], 'parada': [], 'setup_manutencao_offline': []}
    if len(apontamentos) == 0:
        return {'producao': [], 'parada': [], 'setup_manutencao_offline': []}

    def get_details(apt):
        if apt.get('ordem_de_producao'):
            op = frappe.get_doc('Ordem de Producao',
                                apt.get('ordem_de_producao'))
            apt.ordem_de_producao = op
            if apt.ordem_de_producao.item:
                i = frappe.get_doc('Item', apt.ordem_de_producao.item)
                apt.ordem_de_producao.item = i
        if apt.get('operador'):
            o = frappe.get_doc('Operador', apt.get('operador'))
            apt.operador = o
        if apt.get('recurso'):
            o = frappe.get_doc('Recurso', apt.get('recurso'))
            apt.recurso = o
        return apt
    producao = list(map(lambda apt: get_details(apt), filter(lambda apt: apt.get(
        'tipo') == 'Produção', apontamentos)))
    parada = list(map(lambda apt: get_details(apt), filter(lambda apt: apt.get('tipo') == 'Parada' and not apt.get(
        'setup') == 1 and not apt.get('manutencao') == 1 and not apt.get('status_sensor') == 'OFFLINE', apontamentos)))
    setup_manutencao_offline = list(map(lambda apt: get_details(apt), filter(lambda apt: apt.get('tipo') == 'Parada' and (apt.get(
        'setup') == 1 or apt.get('manutencao') == 1 or apt.get('status_sensor') == 'OFFLINE'), apontamentos)))
    return {'producao': producao, 'parada': parada, 'setup_manutencao_offline': setup_manutencao_offline}


def get_cur_turno(recurso, now):
        try:    
            _day = date.today()
            
            disponibilidade = frappe.db.sql(f"""select disponibilidade from tabRecurso 
                                                where name = '{recurso}'""", as_dict=True)
            
            if disponibilidade:
                 disponibilidade = disponibilidade[0]['disponibilidade']
            else:
                return None, None
            
            turno = frappe.db.sql(f"""SELECT turno, tipo,data_para_relatorio FROM tabdisp_rec 
                                      WHERE parent = '{disponibilidade}' 
                                      AND parentfield = '{dias_da_semana[_day.weekday()]}' 
                                      AND (
                                          (inicio <= '{now.strftime('%H:%M:%S')}' AND fim >= '{now.strftime('%H:%M:%S')}') OR
                                          (inicio <= '{now.strftime('%H:%M:%S')}' AND fim < inicio) OR
                                          (fim >= '{now.strftime('%H:%M:%S')}' AND fim < inicio)
                                      )
                                      LIMIT 1""", as_dict=True)
            

            if turno:
                return turno[0]['turno'], turno[0]['tipo'],turno[0]['data_para_relatorio']
            return None, None,None
        
        except Exception as error:
            print("error :", error)

def calcular_apontamento_fechado(recurso,dt_inicio,dt_fim,custo_hora):
        try:
            recurso = frappe.get_doc('Recurso', recurso)
            
            sec = float(time_diff_in_seconds(
                dt_fim, dt_inicio))
            
            hour = float(time_diff_in_hours(
                dt_fim, dt_inicio))
            
            cost_by_hour = hour * custo_hora
            
            centro_custo = recurso.centro_de_custo
            
            total_segundos = sec
            
            total_hr = hour
            
            custo_total = cost_by_hour

            return centro_custo, total_segundos, total_hr ,custo_total

        except Exception as error:
            print('error controler calcular_apontamento_fechado',error)

@frappe.whitelist()
def update_apontamento(apt_name, changes):
    try:
        if not apt_name or not changes:
            return
        
        json_content = json.loads(changes)

        print('json_content',json_content)

        apt = frappe.get_doc('Apontamento', apt_name)

        apt.reload()

        content = json_content.items()

        content = list(content)
        
        content = dict(content)
        
        if apt.status == 'Aberto':  
            status_sensor = frappe.db.sql("select state_sensor,delay_apontamento_parada,delay_apontamento_producao,dt_atualizacao_sensor from `tabRecurso` where name = %s", apt.recurso, as_dict=True)
            
            if not status_sensor[0].get('dt_atualizacao_sensor'):
                _dt_convert = frappe.utils.now_datetime()
            else:
                _dt_convert = datetime.strptime(status_sensor[0].get('dt_atualizacao_sensor'), '%Y-%m-%d %H:%M:%S.%f')

            _tempo_troca_sensor = frappe.utils.now_datetime() - _dt_convert
            _tempo_troca_sensor = _tempo_troca_sensor.total_seconds()

            if _tempo_troca_sensor > status_sensor[0].get('delay_apontamento_parada') or _tempo_troca_sensor > status_sensor[0].get('delay_apontamento_producao'):
                status_sensor = status_sensor[0].get('state_sensor')
                content['status_sensor'] = status_sensor    
            
        content['tp_alt_operador'] = 1
        
        turno,tipo,data_relatorio = get_cur_turno(apt.recurso, utils.now_datetime())
        
        #print('APONTAMENTO',apt.tipo_apontamento)

        if not apt.dt_fim:
            if (apt.tipo == 'Produção' or apt.tipo == 'Setup') or apt.tipo == 'Manutenção':
                content['motivo_de_parada'] = None
                content['desc_motivo_parada'] = None

            if 'tipo' in content:
                if content['tipo'] != apt.tipo:
                    _tipo = content['tipo']
                    content['tipo'] =  apt.tipo
                    
                    content['dt_fim'] = utils.now_datetime()

                    if data_relatorio == 'Mesmo dia':
                        content['dt_inicio_relatorio'] = apt.dt_inicio
                        content['dt_fim_relatorio'] = content['dt_fim']

                    if data_relatorio == 'Dia posterior':
                        content['dt_inicio_relatorio'] = add_days(apt.dt_inicio, 1)
                        content['dt_fim_relatorio'] = add_days(content['dt_fim'], 1)
                    
                    if data_relatorio == 'Dia anterior':
                        content['dt_inicio_relatorio'] = add_days( apt.dt_inicio, -1)
                        content['dt_fim_relatorio'] = add_days(content['dt_fim'], -1)

                    content['status'] = 'Fechado'

                    if (apt.tipo == 'Parada' and content['tipo'] == 'Parada'):
                         content['motivo_de_parada'] = apt.motivo_de_parada
                         content['desc_motivo_parada'] = apt.desc_motivo_parada

                    if content['tipo'] == 'Produção':
                        content['motivo_de_parada'] = None
                        content['desc_motivo_parada'] = None

                    if content['tipo'] == 'Setup' or content['tipo'] == 'Manutenção':
                        content['motivo_de_parada'] = None
                        content['desc_motivo_parada'] = None


                    centro_custo,total_segundos,total_hr,custo_total  = calcular_apontamento_fechado(apt.recurso, apt.dt_inicio, content['dt_fim'], apt.custo_hora)

                    content['centro_custo'] = centro_custo
                    content['total_segundos'] = total_segundos
                    content['total_hr'] = total_hr
                    content['custo_total'] = custo_total

                    _upt_params = [(key, value) for key, value in content.items()]

                    
                    _sql_command = f"""
                        UPDATE `tabApontamento`
                        SET """
                    
                    values = []
                    
                    for key, value in _upt_params:
                        _sql_command += f"{key} = %s, "
                        values.append(value)
                    
                    _sql_command = _sql_command[:-2]  
                    
                    _sql_command += f" WHERE name = '{apt_name}'"
                    
                    frappe.db.sql(_sql_command, values)
                    
                    frappe.db.commit()
                    
                    new_apt = {**apt.as_dict(), 'tipo': _tipo, 'dt_inicio': content['dt_fim_relatorio'], 'dt_fim': None, 'qtde_pecas': 0,
                            'qtde_pecas_refugadas': 0, 'total_segundos': 0, 'total_hr': 0, 'name': None, 'status': 'Aberto',
                            'turno': turno, 'tipo_turno': tipo,'dt_inicio_relatorio': content['dt_fim_relatorio'],'dt_fim_relatorio':None,
                            'tp_alt_operador':content['tp_alt_operador']}
                    
                    new_apt = frappe.get_doc(new_apt)

                    new_apt.insert(ignore_if_duplicate=True,ignore_mandatory=True,ignore_permissions=True)
                    
                    frappe.db.commit()
                    
                    _apontamento_gerado = frappe.db.sql(f"""select * from tabApontamento where name = '{new_apt.name}'""", as_dict=True)
                    
                    res = {
                        'apontamento' : _apontamento_gerado,
                        'site' : frappe.local.site
                    }
                    
         
                    frappe.realtime.publish_realtime('update_apt',res)

                    return new_apt
                else:
                    if 'motivo_de_parada' in content:
                        if not content['motivo_de_parada']:
                            content['motivo_de_parada'] = None
                            content['desc_motivo_parada'] = None
                        else:
                            content['desc_motivo_parada'] = frappe.db.sql(f"""select descricao from `tabMotivo de Parada` where name = '{content['motivo_de_parada']}'""", as_dict=True)
                            content['desc_motivo_parada'] = content['desc_motivo_parada'][0]['descricao']
                    
                    _upt_params = [(key, value) for key, value in content.items()]

                    
                    _sql_command = f"""
                        UPDATE `tabApontamento`
                        SET """
                    
                    values = []
                    
                    for key, value in _upt_params:
                        _sql_command += f"{key} = %s, "
                        values.append(value)
                    
                    _sql_command = _sql_command[:-2]  
                    
                    _sql_command += f" WHERE name = '{apt_name}'"
                    
                    frappe.db.sql(_sql_command, values)
                    
                    frappe.db.commit()

                    _apontamento_gerado = frappe.db.sql(f"""select * from tabApontamento where name = '{apt.name}'""", as_dict=True)
                    res = {
                        'apontamento' : _apontamento_gerado,
                        'site' : frappe.local.site
                    }

                    frappe.realtime.publish_realtime('update_apt',res)

                    return _apontamento_gerado
            else:
                if 'operador' in content:
                    if not content['operador']:
                        content['operador'] = None
                        content['nome_operador'] = None
                    else:
                        content['nome_operador'] = frappe.db.sql(f"""select nome from tabOperador where name = '{content['operador']}'""", as_dict=True)
                        content['nome_operador'] = content['nome_operador'][0]['nome']

                if 'motivo_de_parada' in content:
                    if not content['motivo_de_parada']:
                        content['motivo_de_parada'] = None
                        content['desc_motivo_parada'] = None
                    else:
                        content['desc_motivo_parada'] = frappe.db.sql(f"""select descricao from `tabMotivo de Parada` where name = '{content['motivo_de_parada']}'""", as_dict=True)
                        content['desc_motivo_parada'] = content['desc_motivo_parada'][0]['descricao']
                
                _upt_params = [(key, value) for key, value in content.items()]

                _sql_command = f"""
                    UPDATE `tabApontamento`
                    SET """
                
                values = []
                
                for key, value in _upt_params:
                    _sql_command += f"{key} = %s, "
                    values.append(value)
                
                _sql_command = _sql_command[:-2]  
                
                _sql_command += f" WHERE name = '{apt.name}'"
                
                frappe.db.sql(_sql_command, values)
                
                frappe.db.commit()

                _apontamento_gerado = frappe.db.sql(f"""select * from tabApontamento where name = '{apt.name}'""", as_dict=True)
                
                res = {
                    'apontamento' : _apontamento_gerado,
                    'site' : frappe.local.site
                }
                
                frappe.realtime.publish_realtime('update_apt',res)
                return _apontamento_gerado
        else:
            if 'operador' in content:
                if not content['operador']:
                    content['operador'] = None
                    content['nome_operador'] = None
                else:
                    content['nome_operador'] = frappe.db.sql(f"""select nome from tabOperador where name = '{content['operador']}'""", as_dict=True)
                    content['nome_operador'] = content['nome_operador'][0]['nome']

            if 'motivo_de_parada' in content:
                if not content['motivo_de_parada']:
                    content['motivo_de_parada'] = None
                    content['desc_motivo_parada'] = None
                else:
                    content['desc_motivo_parada'] = frappe.db.sql(f"""select descricao from `tabMotivo de Parada` where name = '{content['motivo_de_parada']}'""", as_dict=True)
                    content['desc_motivo_parada'] = content['desc_motivo_parada'][0]['descricao']
            
            _upt_params = [(key, value) for key, value in content.items()]

            _sql_command = f"""
                UPDATE `tabApontamento`
                SET """
            
            values = []
            
            for key, value in _upt_params:
                _sql_command += f"{key} = %s, "
                values.append(value)
            
            _sql_command = _sql_command[:-2]  
            
            _sql_command += f" WHERE name = '{apt.name}'"
            
            frappe.db.sql(_sql_command, values)
            
            frappe.db.commit()
            
            _apontamento_gerado = frappe.db.sql(f"""select * from tabApontamento where name = '{apt.name}'""", as_dict=True)
            
            return  _apontamento_gerado[0]

    except Exception as e:
        frappe.msgprint(f"Error: {str(e)}")

@frappe.whitelist()
def get_historico_recurso_fechado(recurso_name):
    today = datetime.now().date()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
    query = """
        SELECT *
        FROM `tabApontamento`
        WHERE recurso = %s AND status = 'Fechado' AND dt_fim BETWEEN %s AND %s
        ORDER BY name DESC
    """
    
    historico = frappe.db.sql(query, (recurso_name, start_of_day, end_of_day), as_dict=True)
    return historico

@frappe.whitelist()
def get_disponibilidade_diaria_em_producao(recurso_name):
    today = utils.nowdate()
    disponibilidade = f'{recurso_name}: {today}'
    disponibilidade = frappe.db.get_value(
        'Disponibilidade Diaria', disponibilidade, 'percentual_producao')
    return disponibilidade if disponibilidade else 0


@frappe.whitelist()
def get_all_operador(limit=0):
    operadores = frappe.db.get_all(
        'Operador', filters={'status': 'Ativo'}, fields="*")
    order_by = 'dt_inicio desc' if not limit == 0 else None
    operadores = list(map(lambda o: {**o, 'apontamentos': frappe.db.get_all('Apontamento',
                      fields="*", filters={'operador': o.name}, limit=limit, order_by=order_by)}, operadores))
    return operadores


@frappe.whitelist()
def get_all_recurso(limit=None, recurso=None, origem=None, today=0):
    
    filters = {'status': 'Ativo', 'tipo_apontamento': 'NXIOT'}
    
    if recurso:
        filters['name'] = recurso
    
    recursos = frappe.db.get_all('Recurso', filters=filters, fields="*")
    
    early_hour = time(hour=0, minute=0, second=0)
    last_hour = time(hour=23, minute=59, second=59)
    today = utils.now_datetime().date()
    today_end = datetime.combine(today, early_hour)
    today_start = datetime.combine(today, last_hour)
    order_by = 'dt_inicio desc' if not limit else None

    recursos = list(map(lambda o: {**o, 'apontamentos': frappe.db.get_all('Apontamento', filters={'recurso': o.name}
                                                                          if not today
                                                                          else {'recurso': o.name, 'dt_inicio': [
                                                                              'between', [today_start.isoformat(), today_end.isoformat()]]},
                                                                          order_by=order_by,
                                                                          limit=limit or 0,
                                                                          fields="*")}, recursos))
    return recursos


@frappe.whitelist()
def get_all_ordem_de_producao(limit=0, op=None):
    filters = {
        'status_op': 'Aberto',
        'estagio': 'Em produção'
    }

    if op is not None:
        res = frappe.get_doc('Ordem de Producao', op)
        return res

    ops = frappe.db.get_all('Ordem de Producao', filters=filters, fields='*')
    order_by = 'dt_inicio desc' if limit != 0 else None

    ops = list(map(lambda o: {
        **o,
        'item': frappe.get_doc('Item', o.item) if o.item else None,
        'apontamentos': frappe.db.get_all('Apontamento', fields='*', filters={'ordem_de_producao': o.name}, order_by=order_by, limit=limit)
    }, ops))

    return ops


@frappe.whitelist()
def listar_turnos(filtro={}):
    try:
        filtros = json.loads(filtro)
        filtro_ajustado = filter_front(filtros)

        data_inicio = datetime.strptime(filtro_ajustado['dt_inicio'], "%Y-%m-%d")
        data_fim = datetime.strptime(filtro_ajustado['dt_fim'], "%Y-%m-%d")

        diferenca = data_fim - data_inicio
        
        _dias_semana_query = []
        
        if not diferenca.days:
            _dias_semana_query.append(dias_da_semana[data_inicio.weekday()])
        else:
            for day in range((diferenca.days + 1)):
                if day == 0:
                    data = data_inicio
                else:
                    data = data_inicio + timedelta(days=day)
    
                if dias_da_semana[data.weekday()] not in _dias_semana_query:
                    _dias_semana_query.append(dias_da_semana[data.weekday()])

        turnos = frappe.db.get_all('Turno', fields='*')
        dias_semana_str = ','.join(f"'{dia}'" for dia in _dias_semana_query)

        query = f"""
                SELECT td.turno FROM tabRecurso r, tabdisp_rec td
                WHERE r.disponibilidade = td.parent
                AND td.tipo = 'Disponível'
                AND td.parentfield IN ({dias_semana_str})
                AND r.name IN ({format_qry(filtro_ajustado['recurso'])})
                GROUP BY td.turno 
            """
        
        turnos = frappe.db.sql(query, as_dict=1)  
        return turnos
    except Exception as e:
        print('error listar_turnos',str(e))


@frappe.whitelist()
def get_files_ordem_de_producao(op):

    ordem_de_producao = frappe.get_doc('Ordem de Producao', op)
    desenhos = [
        {
            'arquivo': desenho.arquivo,
            'descricao': desenho.descricao
        }
        for desenho in ordem_de_producao.desenhos
    ]

    return desenhos


@frappe.whitelist()
def get_all_filter_by_date_apontamento(start_date=None, end_date=None,recurso=None):
    if start_date and end_date:
        filters = [['dt_inicio', 'between', [start_date, end_date]]]
        
        if recurso:
            filters.append(['recurso', '=', recurso])
        apontamentos = frappe.db.get_all('Apontamento', filters=filters, fields='*', order_by='dt_inicio desc')
        
        return apontamentos
    return


@frappe.whitelist()
def get_all_motivos_de_parada(tp_Parada=None, maquina_sel=None):

    filtro_maq = {'name': maquina_sel}
       
    recursos = frappe.db.get_all('Recurso', filters=filtro_maq, fields='motivo_de_parada_padrao')
    
    motivos_padrao = {r['motivo_de_parada_padrao'] for r in recursos if r['motivo_de_parada_padrao']}
    
    filters = {'status': 'Ativo'}
    
    if tp_Parada == 'Setup':
        filters['setup'] = 1
    elif tp_Parada == 'Manutenção':
        filters['manutencao'] = 1
    
    motivos_parada = frappe.db.get_all('Motivo de Parada', filters=filters, fields="*")
    
    motivos_filtrados = [mp for mp in motivos_parada if str(mp['name']) not in motivos_padrao]
    
    return motivos_filtrados


@frappe.whitelist()
def criar_novo_apontamento(recurso, tipo='Produção'):
    novo_apontamento = frappe.get_doc({
        'doctype': 'Apontamento',
        'status': 'Aberto',
        'tipo': tipo,
        'recurso': recurso,
        'origem_apontamento': 'NXIOT',
    })

    novo_apontamento.insert()

    frappe.db.commit()

    return get_all_recurso(15, recurso, origem="criar_novo_apontamento", today=1)



@frappe.whitelist()
def get_infos_disp_resumida(filtro={}):

    filtros = json.loads(filtro)
    dispResumida = DispResumida()
    resultado = dispResumida.disp_resumida_infos(filtros)
    
    return resultado

@frappe.whitelist()
def get_infos_desempenho(filtro={}):

    filtros = json.loads(filtro)

    info_desempenho = Desempenho()
    resultado = info_desempenho.get_info_desempenho(filtros)

    return resultado

@frappe.whitelist()
def relatorio_de_motivos_de_parada(filtro={}):

    filtros = json.loads(filtro)
    _charts = ParetoParadas()
    resultado = _charts.pareto_paradas(filtros)

    return resultado

@frappe.whitelist()
def lista_recursos_abertos(filtro={}):

    filtros = json.loads(filtro)
    _charts = MaquinaStatus()
    resultado = _charts.get_maq_status_info(filtros)

    return resultado


@frappe.whitelist()
def generate_token_iot():
    _config_iot = ConfigIot()
    return _config_iot.generate_token()


@frappe.whitelist()
def get_config_iot():
    _config_iot = ConfigIot()
    return _config_iot.get_config_iot()


@frappe.whitelist()
def update_config_iot(payload={}):
    if not payload:
        return {"error": "Payload não informado", "status": 400}
    _config_iot = ConfigIot()
    return _config_iot.update_config_iot(payload)

@frappe.whitelist()
def get_token_dash():
    _config_iot = ConfigIot()
    return _config_iot.get_token()
import cherrypy
import json
from datetime import datetime, timezone

class AlertSystem(object):
    exposed = True

    # Dati memorizzati nella classe (memoria del server)
    thresholds = {} # Conterrà dict del tipo: {"temperature": {"min": 10, "max": 30}}
    alerts = []     # Conterrà liste di dict per ogni allarme generato

    def GET(self, *uri, **params):
        # Controllo che ci sia almeno un segmento nell'URL
        if len(uri) == 0:
            raise cherrypy.HTTPError(400, "Bad request: Specificare un endpoint (/threshold o /alerts)")

        action = uri[0] # Il primo pezzo dell'URL decide cosa fare

        if action == "threshold":
            # Ritorna tutte le soglie configurate
            return json.dumps(self.thresholds).encode("utf-8")

        elif action == "alerts":
            # Se l'URL ha un secondo segmento, filtriamo per quel sensore (es. /alerts/temperature)
            if len(uri) > 1:
                nome_sensore = uri[1]
                # Creiamo una lista filtrata che contiene solo gli allarmi di quel sensore
                allarmi_filtrati = [a for a in self.alerts if a.get("sensor") == nome_sensore]
                return json.dumps(allarmi_filtrati).encode("utf-8")
            else:
                # Altrimenti, /alerts ritorna tutti gli allarmi globali
                return json.dumps(self.alerts).encode("utf-8")

        else:
            raise cherrypy.HTTPError(404, "Not found: Endpoint non esistente")


    def POST(self, *uri, **params):
        if len(uri) == 0:
            raise cherrypy.HTTPError(400, "Bad request: Specificare un endpoint (/threshold o /check)")

        action = uri[0]
        
        # Leggiamo il JSON inviato dal client nel body
        body = cherrypy.request.json

        # Assicuriamoci che il sensore sia sempre specificato nel body
        if "sensor" not in body:
            raise cherrypy.HTTPError(400, "Bad request: Il campo 'sensor' e' obbligatorio nel JSON")
            
        nome_sensore = body["sensor"]

        if action == "threshold":
            # 1. Recupero i valori inviati
            min_val = body.get("min")
            max_val = body.get("max")
            
            # 2. Validazione: min deve essere strettamente minore di max 
            if min_val is None or max_val is None or min_val >= max_val:
                raise cherrypy.HTTPError(400, "Bad request: 'min' e 'max' richiesti. 'min' deve essere < 'max'")
            
            # 3. Salvo la configurazione nel dizionario
            self.thresholds[nome_sensore] = {"min": min_val, "max": max_val}
            
            return json.dumps({"message": f"Soglia salvata per {nome_sensore}"}).encode("utf-8")

        elif action == "check":
            # 1. Recupero il valore da controllare
            valore = body.get("value")
            
            if valore is None:
                raise cherrypy.HTTPError(400, "Bad request: Il campo 'value' e' richiesto")
                
            # 2. Controllo cross-resource: verifico se esistono le soglie per questo sensore 
            if nome_sensore not in self.thresholds:
                raise cherrypy.HTTPError(404, f"Not found: Nessuna soglia configurata per {nome_sensore}")
            
            t_min = self.thresholds[nome_sensore]["min"]
            t_max = self.thresholds[nome_sensore]["max"]
            
            # 3. Controllo del range e creazione dell'allarme con label direzionale 
            is_alert = False
            direction = ""
            
            if valore < t_min:
                is_alert = True
                direction = "LOW"
            elif valore > t_max:
                is_alert = True
                direction = "HIGH"
                
            if is_alert:
                dettagli_allarme = {
                    "sensor": nome_sensore,
                    "value": valore,
                    "direction": direction,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                # Salvo l'allarme nella memoria
                self.alerts.append(dettagli_allarme)
                
                # Risposta in caso di allarme come da esempio 
                response = {
                    "alert": True,
                    "details": dettagli_allarme
                }
                return json.dumps(response).encode("utf-8")
            else:
                # Risposta se il valore rientra nel range stabilito
                return json.dumps({"alert": False, "message": "Valore nella norma"}).encode("utf-8")

        else:
            raise cherrypy.HTTPError(404, "Azione non consentita")


if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.json_in.on': True,  # <-- AGGIUNTA FONDAMENTALE PER LEGGERE LE POST
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }
    
    # Rinominiamo e montiamo la nostra nuova classe
    cherrypy.tree.mount(AlertSystem(), '/', conf)

    cherrypy.config.update({'server.socket_host': '127.0.0.1'})
    cherrypy.config.update({'server.socket_port': 9090})
    cherrypy.engine.start()
    cherrypy.engine.block()
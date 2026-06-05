import cherrypy
import json
import time


class SmartHomeLogService(object):
    exposed = True
    
    id=0
    logs = []

    def createSenML_URI(self, uri, params=None):
        finalURI = {
            "s": "log" 
        }
        
        if len(uri) > 0:
            finalURI["bn"] = uri[0]  # Stanza
            
        if params:
            finalURI["params"] = params

        return finalURI

    def AddLog(self, value):
        self.logs.append(value)

    ## Funzione per ricevere un log da un sensore o attuatore e aggiungerlo alla lista dei log
    def POST(self, *uri, **params):
        if(len(uri) == 0):
            raw = cherrypy.request.body.read()
            timestamp = time.time()
            
            # Controllo correttezza del pacchetto
            if not raw:
                raise cherrypy.HTTPError(400, "Bad request: Empty body")
            
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                raise cherrypy.HTTPError(400, "Bad request: Invalid JSON body")
            
            #controllo che il pacchetto contenga i campi necessari (bn, e) e che e sia una lista con almeno un elemento che contenga i campi n, v, u
            
            if "bn" not in body or "e" not in body:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if not isinstance(body["e"], list):
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"]) != 1:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if len(body["e"][0]) != 3:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "n" not in body["e"][0] or "v" not in body["e"][0] or "u" not in body["e"][0]:
                raise cherrypy.HTTPError(422, "Bad request: Unprocessable Entity")
            
            if "bt" not in body:
                timestamp = time.time()
                body = {"bt": timestamp, **body}
            else:
                body["bt"] = timestamp
            
            body = {"id": SmartHomeLogService.id, **body}
            SmartHomeLogService.id += 1
            
            self.AddLog(body)
            return json.dumps({"status": "success", "log_id": SmartHomeLogService.id - 1}).encode("utf-8")
    
    ## Funzione per ottenere tutti i log, con la possibilità di filtrare per stanza e per timestamp
    def GET(self, *uri, **params):          
        # GET /log
        if(len(uri) == 0 and len(params) == 0):
            #self.AddLog(self.createSenML_URI(uri))
            return json.dumps(self.logs).encode("utf-8")
        
        # GET /log/{room}
        if (len(uri) == 1 and len(params) == 0):
            return json.dumps(self.get_logs_by_room(self.logs, uri[0])).encode("utf-8")
        
        # GET /log?room={room}&since={timestamp}
        response = self.logs
        if (len(uri) == 0 and len(params) <= 2):
            for key in params.keys():
                if key not in ["room", "since"]:
                    raise cherrypy.HTTPError(400, "Bad request: Invalid query parameters. Valid parameters are 'room' and 'since'. Example: /log?room=bedroom&since=1234567890")
            if "room" in params:
                response = self.get_logs_by_room(response, params.get("room"))
            if "since" in params:
                response = self.get_logs_by_time(response, float(params.get("since")))
            return json.dumps(response).encode("utf-8")
        
        raise cherrypy.HTTPError(400, "Bad request: Invalid URI format. Valid formats are /log, /log/{room}, /log?room={room}&since={timestamp}. Example: /log?room=bedroom&since=1234567890")
        
        if(len(uri) == 0):

            # Da sistemare (codice inguardabile)
            if(len(params)>0):
                if("room" in params and "since" in params):
                    room = params.get("room")
                    since = float(params.get("since"))
                    for log in self.logs:
                        if( ("bn" in log["VAL"]) and log["VAL"]["bn"] == room and log["EPOCH"] >= since):
                            response.append(log)
                    #self.AddLog(self.createSenML_URI(uri))
                    return json.dumps(response).encode("utf-8")


                if("room" in params ):
                    room = params.get("room")
                    for log in self.logs:
                        if( ("bn" in log["VAL"]) and log["VAL"]["bn"] == room ):
                            response.append(log)

                if("since" in params ):
                    since = float(params.get("since"))
                    for log in self.logs:
                        if(log["EPOCH"] >= since ):
                            response.append(log)

                #self.AddLog(self.createSenML_URI(uri))
                return json.dumps(response).encode("utf-8")
            
            #self.AddLog(self.createSenML_URI(uri))
            return json.dumps(self.logs).encode("utf-8")

        room = uri[0]
        for log in self.logs:
            if( ("bn" in log["VAL"]) and log["VAL"]["bn"] == room ):
                response.append(log)

            # GET http://127.0.0.1:9090/log/bedroom?from=1234&limit=10
            # uri    → ('bedroom',)
            # params → {'from': '1234', 'limit': '10'}

        return json.dumps(response).encode("utf-8")

    ## Funzione per eliminare i log precedenti a un certo timestamp
    def DELETE(self, *uri, **params):
        try:
            if(len(uri) == 0 and len(params) == 1 and ("before" in params)):
                epoch = float(params.get("before"))
                # Sovrascrive la lista mantenendo solo gli elementi con EPOCH >= epoch
                self.logs[:] = [log for log in self.logs if log["bt"] >= epoch]
                #self.AddLog(self.createSenML_URI(uri, params))
                return json.dumps({"status": "success", "deleted_before": epoch}).encode("utf-8")
            else:
                raise cherrypy.HTTPError(400, "Bad request: Not found")
        except:
            raise cherrypy.HTTPError(500, "Server error")

    def get_logs_by_room(self, paramLogs, room):
        response = []
        for log in paramLogs:
            if room in log["bn"]:
                response.append(log)
        return response
    
    def get_logs_by_time(self, paramLogs, since):
        response = []
        for log in paramLogs:
            if log["bt"] >= since:
                response.append(log)
        return response
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
        timestamp = time.time()
        self.logs.append({"ID": SmartHomeLogService.id ,"EPOCH": timestamp, "VAL": value})
        SmartHomeLogService.id += 1

    def GET(self, *uri, **params):
        response = []
        if(len(uri) == 0):

            # Da sistemare (codice inguardabile)
            if(len(params)>0):
                if("room" in params and "since" in params):
                    room = params.get("room")
                    since = float(params.get("since"))
                    for log in self.logs:
                        if( ("bn" in log["VAL"]) and log["VAL"]["bn"] == room and log["EPOCH"] >= since):
                            response.append(log)
                    self.AddLog(self.createSenML_URI(uri))
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

                self.AddLog(self.createSenML_URI(uri))
                return json.dumps(response).encode("utf-8")
            
            self.AddLog(self.createSenML_URI(uri))
            return json.dumps(self.logs).encode("utf-8")

        room = uri[0]
        for log in self.logs:
            if( ("bn" in log["VAL"]) and log["VAL"]["bn"] == room ):
                response.append(log)

            # GET http://127.0.0.1:9090/log/bedroom?from=1234&limit=10
            # uri    → ('bedroom',)
            # params → {'from': '1234', 'limit': '10'}

        return json.dumps(response).encode("utf-8")



    def DELETE(self, *uri, **params):
        try:
            if(len(uri) == 0 and len(params) == 1 and ("before" in params)):
                epoch = float(params.get("before"))
                # Sovrascrive la lista mantenendo solo gli elementi con EPOCH >= epoch
                self.logs[:] = [log for log in self.logs if log["EPOCH"] >= epoch]
                self.AddLog(self.createSenML_URI(uri, params))
                return json.dumps({"status": "success", "deleted_before": epoch}).encode("utf-8")
            else:
                raise cherrypy.HTTPError(400, "Bad request: Not found")
        except:
            raise cherrypy.HTTPError(500, "Server error")


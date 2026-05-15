import cherrypy
import json
import time

class SmartHomeLogService(object):
    exposed = True

    logs = []

    def createSenML_URI(self, uri):
        finalURI = {
            "s": "log" 
        }
        
        if len(uri) > 0:
            finalURI["bn"] = uri[0]  # Stanza
            
        # if len(uri) > 1:
        #     finalURI["n"] = uri[1]   # Sensore

        return finalURI
    

    def AddLog(self, value):
        timestamp = time.time()
        self.logs.append({"time": timestamp, "value": value})

    def GET(self, *uri, **params):
        response = []
        if(len(uri) == 0):

            if(len(params)>0):
                if("room" in params and "since" in params):
                    room = params.get("room")
                    since = float(params.get("since"))
                    for log in self.logs:
                        if( ("bn" in log["value"]) and log["value"]["bn"] == room and log["time"] >= since):
                            response.append(log)
                    self.AddLog(self.createSenML_URI(uri))
                    return json.dumps(response).encode("utf-8")


                if("room" in params ):
                    room = params.get("room")
                    for log in self.logs:
                        if( ("bn" in log["value"]) and log["value"]["bn"] == room ):
                            response.append(log)

                if("since" in params ):
                    since = float(params.get("since"))
                    for log in self.logs:
                        if(log["time"] >= since ):
                            response.append(log)

                self.AddLog(self.createSenML_URI(uri))
                return json.dumps(response).encode("utf-8")
            
            self.AddLog(self.createSenML_URI(uri))
            return json.dumps(self.logs).encode("utf-8")

        room = uri[0]
        for log in self.logs:
            if( ("bn" in log["value"]) and log["value"]["bn"] == room ):
                response.append(log)

            # GET http://127.0.0.1:9090/log/bedroom?from=1234&limit=10
            # uri    → ('bedroom',)
            # params → {'from': '1234', 'limit': '10'}



        return json.dumps(response).encode("utf-8")




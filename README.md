Práctica 4 - Maekawa Algorithm
Joan Pascual Alcaraz

Proyecto sobre comunicación entre nodos con la implementación del algoritmo de 
Maekawa para la exclusión mútua donde los nodos compiten entre sí para 
acceder a la sección crítica. Un nodo tiene dos hilos para gestionar la 
comunicación: ServerNode (recibir peticiones) y NodeSend (enviar peticiones).

El algoritmo de Maekawa se basa en la inclusión de un grupo de votantes para 
cada nodo, de modo que si un nodo quiere acceder a la sección crítica debe 
enviar un mensaje a su grupo, y si todos le permiten el acceso entra a la 
sección crítica. Para que se garantice la exclusión mútua es necesario que el 
grupo cumpla algunas condiciones.

Para desarrollar el algoritmo de Maekawa he modificado el código de node.py, 
en especial la función state(), he implementado la función process_message() 
de nodeServer.py y he añadido la función update() a nodeSend.py. Para llevarlo 
a cabo he consultado y utilizado parte del siguiente código:
https://github.com/yvetterowe/Maekawa-Mutex

Para lanzar el proyecto hay que ejecutar el programa main.py y se iniciará la 
comunicación entre nodos. Actualmente funciona para 3 y 7 nodos, ya que he 
implementado los grupos de votación manualmente para estos dos N, para asegurarme 
el buen funcionamiento del algoritmo, ya que con una creación de los grupos 
automática había problemas de bloqueo entre los nodos. El número de nodos se 
puede cambiar en el config, mientras que los dos grupos de votación están 
en la función init() de node.py. Por defecto está definido para 7 nodos.
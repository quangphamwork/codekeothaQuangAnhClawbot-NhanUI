FROM cyberbotics/webots.cloud:R2023b-ubuntu22.04
ARG PROJECT_PATH
RUN mkdir -p $PROJECT_PATH
COPY . $PROJECT_PATH
RUN cd $PROJECT_PATH/controllers/my_controller && make clean && make
RUN cd $PROJECT_PATH/controllers/sumo_arena && make clean && make

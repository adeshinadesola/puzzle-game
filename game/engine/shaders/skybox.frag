#version 330 core

layout(location = 0)out vec4 frag_color;

uniform int level;
uniform float u_time; // in seconds
uniform vec2 u_resolution;

float dist(vec2 p0, vec2 pf) {
    return sqrt((pf.x - p0.x) * (pf.x - p0.x) + (pf.y - p0.y) * (pf.y - p0.y));
}

vec4 lv0(float t) {
    vec2 pos = gl_FragCoord.xy;
    vec2 origin = vec2(u_resolution.x * 0.5, u_resolution.y *- 0.1);
    
    vec3 core_color = vec3(0.9686, 0.8118, 0.502);
    vec3 bg_color = vec3(0.7059, 0.5255, 0.4314);
    
    float d = clamp(dist(origin, pos) * cos(t) * 0.003, 0.0, 1.0);
    vec3 new_color = mix(core_color, bg_color, d);
    return vec4(new_color, 1.0);
}

void main() {
    if (level == 0) {
        frag_color = lv0(u_time);
    } else {
        frag_color = vec4(0.9, 0.9, 0.9, 1.0);
    }
}
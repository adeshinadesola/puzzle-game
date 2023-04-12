#version 330 core

// Blending functions from: https://github.com/jamieowen/glsl-blend

layout (location = 0) out vec4 fragColor;

in vec2 uv_0;

uniform vec4 v_color;
uniform sampler2D u_texture_0;
uniform int blend_mode;

vec3 multiply(vec3 a, vec3 b) {
  return vec3(a[0] * b[0], a[1] * b[1], a[2] * b[2]);
}

vec3 multiply(vec3 base, vec3 blend, float opacity){
  return (multiply(base, blend) * opacity + base * (1.0 - opacity));
}

float _overlay(float base, float blend) {
	return base<0.5?(2.0*base*blend):(1.0-2.0*(1.0-base)*(1.0-blend));
}

vec3 overlay(vec3 base, vec3 blend) {
	return vec3(_overlay(base.r,blend.r),_overlay(base.g,blend.g),_overlay(base.b,blend.b));
}

vec3 overlay(vec3 base, vec3 blend, float opacity) {
	return (overlay(base, blend) * opacity + base * (1.0 - opacity));
}

float _reflect(float base, float blend) {
	return (blend==1.0)?blend:min(base*base/(1.0-blend),1.0);
}

vec3 reflects(vec3 base, vec3 blend) {
	return vec3(_reflect(base.r,blend.r), _reflect(base.g,blend.g), _reflect(base.b,blend.b));
}

vec3 reflects(vec3 base, vec3 blend, float opacity) {
	return (reflects(base, blend) * opacity + base * (1.0 - opacity));
}

void main() {
  vec3 imageColor = texture(u_texture_0, uv_0).rgb;
  vec3 fillColor;
  if (blend_mode == 1) {
    fillColor = overlay(imageColor, v_color.rgb, v_color.a);
  } else if (blend_mode == 2) {
    fillColor = multiply(imageColor, v_color.rgb, v_color.a);
  } else if (blend_mode == 3) {
    fillColor = reflects(imageColor, v_color.rgb, v_color.a);
  } else {
    fillColor = v_color.rgb;
  }
  fragColor = vec4(fillColor, 1.0);
}
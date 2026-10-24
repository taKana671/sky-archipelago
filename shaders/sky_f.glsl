#version 430
in vec3 vtx_dir;
uniform vec3 sun_direction;
out vec4 p3d_FragColor;

void main() {
    vec3 dir = normalize(vtx_dir);
    
    vec3 sky_top = vec3(0.05, 0.40, 0.85);
    vec3 sky_horizon = vec3(0.65, 0.82, 0.95);
    
    // Gradient based on altitude (Z-Axis)
    float h = max(dir.z, 0.0);
    vec3 sky_color = mix(sky_horizon, sky_top, pow(h, 0.75));
    
    float sun_glow = max(dot(dir, sun_direction), 0.0);
    sky_color += vec3(1.0, 1.0, 0.95) * pow(sun_glow, 128.0); 
    sky_color += vec3(0.3, 0.4, 0.4) * pow(sun_glow, 8.0);  
    
    p3d_FragColor = vec4(sky_color, 1.0);
}
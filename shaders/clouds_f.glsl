#version 430

in vec2 terrain_uv;
in vec3 vtx_pos;

uniform float osg_FrameTime;
uniform vec3 sun_direction;
uniform mat4 p3d_ViewMatrixInverse;
uniform vec3 plane_center;

out vec4 p3d_FragColor;

// Pseudorandom number generation using hash functions
float hash(vec3 p) {
    p = fract(p * vec3(443.8975, 397.2973, 491.1871));
    p += dot(p.xyz, p.yzx + 19.19);
    return fract(p.x * p.y * p.z);
}

// 3D value noise to smoothly interpolate values in 3D space.
float valueNoise3D(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f); 

    return mix(
        mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
            mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
        mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
            mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z
    );
}

float fbm(vec3 p) {
    p.xy += osg_FrameTime * 0.1; 
    
    float v = 0.0;
    float amplitude = 0.5;
    vec3 shift = vec3(100.0);
    for (int i = 0; i < 4; i++) { 
        v += amplitude * valueNoise3D(p);
        p = p * 2.0 + shift;
        amplitude *= 0.5;
    }
    return v;
}

// Density function
float getCloudDensity(vec3 pos) {
    vec3 sample_pos = pos * 0.02;
    float d = fbm(sample_pos) - 0.45; 

    // Thickness control (z from -300 to 500)
    float height_fade = smoothstep(-500.0, -450.0, pos.z) * smoothstep(-300.0, -320.0, pos.z);
    d *= height_fade;

    // Circular fade-out (Precisely cropped based on the distance from the center coordinates of the Plane)
    float dist = length(pos.xy - plane_center.xy);
    float world_fade = smoothstep(1400.0, 1100.0, dist);
    d *= world_fade;

    return max(d, 0.0);
}

void main() {
    // Get the camera's world position
    vec3 real_camera_pos = p3d_ViewMatrixInverse.xyz;

    // Generate light rays
    vec3 ro = vtx_pos; 
    vec3 rd = normalize(vtx_pos - real_camera_pos);

    int max_steps = 45;       
    float step_size = 4.5;    

    float total_density = 0.0; 
    float total_light = 0.0;   

    vec3 current_pos = ro;    

    // Start of the ray marching loop
    for (int i = 0; i < max_steps; i++) {
        float density = getCloudDensity(current_pos);

        if (density > 0.01) {
            // Self shadow
            vec3 shadow_pos = current_pos + sun_direction * 15.0;
            float shadow_density = getCloudDensity(shadow_pos);
            
            float light_absorption = exp(-shadow_density * 4.5);
            total_light += density * light_absorption * (1.0 - total_density);

            // Calculate the total density
            total_density += density * (1.0 - total_density);

            if (total_density >= 0.95) {
                total_density = 1.0;
                break;
            }
        }

        // Move the beam in the direction of the line of sight
        current_pos += rd * step_size;
    }

    // Calculating the final cloud colors and shading
    vec3 cloud_color = vec3(0.95, 0.96, 0.98);
    vec3 shadow_color = vec3(0.42, 0.42, 0.52);

    // Ambient occlusion
    // Slightly darken and lower the base of the clouds depending on altitude (depth) to emphasize the sense of depth
    float height_factor = smoothstep(-300.0, -480.0, current_pos.z);
    vec3 local_shadow_color = mix(shadow_color, shadow_color * 0.75, height_factor);

    // Calculating the glow (highlights) along the edges caused by forward scattering of sunlight
    float rim = max(dot(sun_direction, -rd), 0.0);
    vec3 highlight_color = cloud_color + vec3(0.2) * pow(rim, 4.0) * total_light;
    
    // Calculate the final color after applying the two effects
    vec3 final_sky_sea = mix(local_shadow_color, highlight_color, total_light);

    p3d_FragColor = vec4(final_sky_sea, total_density);
}
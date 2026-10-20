#version 430

in vec2 texcoord;
in vec4 vertex_color;
in vec3 vtx_view_pos;

uniform sampler2D p3d_TextureModulate;

uniform struct PandaMaterial {
    vec4 diffuse;
} p3d_Material;

// The structure for fog automatically sent by Panda3D
uniform struct {
    vec4 color;
    float density;
} p3d_Fog;

out vec4 p3d_FragColor;

void main() {
    // Color Calculations for Existing Grass
    vec4 base_grass_color = clamp(vertex_color * p3d_Material.diffuse * texture(p3d_TextureModulate, texcoord), 0.0, 1.0);

    // Calculate the straight-line distance from the camera to this blade of grass
    float dist = length(vtx_view_pos); 
    
    // Calculate the decay rate of the exponential fog (the value of 0.00015 set in Python is automatically applied)
    float fog_factor = exp(-dist * p3d_Fog.density);
    
    // If 0.45 is set to a higher value, the colors of the distant islands will appear even more vivid and saturated.
    fog_factor = mix(0.45, 1.0, fog_factor); 
    fog_factor = clamp(fog_factor, 0.0, 1.0);

    // Blend only the RGB components of the grass with the light blue color of the sky (p3d_Fog.color) based on distance
    vec3 fogged_grass_rgb = mix(p3d_Fog.color.rgb, base_grass_color.rgb, fog_factor);

    p3d_FragColor = vec4(fogged_grass_rgb, base_grass_color.a);
}

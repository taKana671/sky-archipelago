#version 430

uniform sampler2D tex_ground;
uniform sampler2D tex_grass1;
uniform sampler2D tex_grass2;
uniform sampler2D tex_mask;

uniform struct {
    sampler2D data_texture;
    sampler2D heightfield;
    int view_index;
    int terrain_size;
    int chunk_size;
} ShaderTerrainMesh;


in vec2 terrain_uv;
in vec3 vtx_pos;
in vec3 vtx_normal;
out vec4 p3d_FragColor;


// Three-Dimensional Mapping
vec4 getTriplanarBlend(sampler2D tex, vec3 pos, vec3 normal) {
    float repeat_count = 2.0; 
    vec3 uv_pos = pos * (repeat_count / 256.);

    // Sampling from three directions (XY plane, XZ plane, YZ plane)
    vec4 col_x = texture(tex, uv_pos.zy);
    vec4 col_y = texture(tex, uv_pos.zx);
    vec4 col_z = texture(tex, uv_pos.xy);

    // Calculate the weight that determines which texture to strongly use based on the slope's angle (normal).
    vec3 blend_weights = pow(abs(normal), vec3(4.0));
    blend_weights = max(blend_weights, 0.00001);
    blend_weights /= (blend_weights.x + blend_weights.y + blend_weights.z);

    return col_x * blend_weights.x + col_y * blend_weights.y + col_z * blend_weights.z;
}


void main() {
    // If the alpha value is less than 0.01, discard the rendering of that pixel.
    float mask = texture(tex_mask, terrain_uv).r;

    if (mask == 0.0) {
        discard;
        return;
    }

    // Retrieve the percentage of original height(0.0–1.0) from the heightmap.
    float h = texture(ShaderTerrainMesh.heightfield, terrain_uv).r;
    
    vec3 calculated_normal = normalize(cross(dFdx(vtx_pos), dFdy(vtx_pos)));

    vec4 color_ground = getTriplanarBlend(tex_ground, vtx_pos, calculated_normal);
    vec4 color_grass1 = getTriplanarBlend(tex_grass1, vtx_pos, calculated_normal);
    vec4 color_grass2 = getTriplanarBlend(tex_grass2, vtx_pos, calculated_normal);

    
    // If the height h of the heightmap exceeds 0.003, grass1 begins to appear;
    // when it reaches 0.30 or higher, the entire area consists solely of grass1.
    float blend_ground_grass1 = smoothstep(0.003, 0.30, h);
    float blend_grass1_grass2  = smoothstep(0.30,  0.85, h);

    vec4 final_color = color_ground;
    final_color = mix(final_color, color_grass1, blend_ground_grass1);
    final_color = mix(final_color, color_grass2, blend_grass1_grass2);

    p3d_FragColor = final_color;
}
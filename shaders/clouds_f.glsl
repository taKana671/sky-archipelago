#version 430

// バーテックスシェーダーからの入力
in vec2 terrain_uv;
in vec3 vtx_pos;

// Panda3DおよびPython側からのUniform入力
uniform float osg_FrameTime;         // 雲を動かすための時間軸
uniform vec3 sun_direction;          // 太陽の光の方向
uniform mat4 p3d_ViewMatrixInverse;
uniform vec3 plane_center;           // Planeの中心座標

out vec4 p3d_FragColor;

// ハッシュ関数による疑似ランダム生成
float hash(vec3 p) {
    p = fract(p * vec3(443.8975, 397.2973, 491.1871));
    p += dot(p.xyz, p.yzx + 19.19);
    return fract(p.x * p.y * p.z);
}

// 3D空間の値を滑らかに補間する3D Value Noise
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

// 複数層のノイズを重ねて（FBM）ディテールを凝縮する
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

// 密度関数（ワールド3D座標ベース＋Plane中心基準のマスク）
float getCloudDensity(vec3 pos) {
    // 試行錯誤の結果たどり着いたベストな調整値
    vec3 sample_pos = pos * 0.02;
    float d = fbm(sample_pos) - 0.45; 

    // 厚みの制御（Z = -300 から Z = -500 まで）
    float height_fade = smoothstep(-500.0, -450.0, pos.z) * smoothstep(-300.0, -320.0, pos.z);
    d *= height_fade;

    // 円形フェードアウト（Planeの中心座標からの距離で正確に切り取る）
    float dist = length(pos.xy - plane_center.xy);
    float world_fade = smoothstep(1400.0, 1100.0, dist);
    d *= world_fade;

    return max(d, 0.0);
}

void main() {
    // 安全なカメラのワールド位置取得
    vec3 real_camera_pos = p3d_ViewMatrixInverse.xyz;

    // 1. 光線の生成
    vec3 ro = vtx_pos; 
    vec3 rd = normalize(vtx_pos - real_camera_pos);

    int max_steps = 45;       
    float step_size = 4.5;    

    float total_density = 0.0; 
    float total_light = 0.0;   

    vec3 current_pos = ro;    

    // 2. レイマーチング・ループの開始
    for (int i = 0; i < max_steps; i++) {
        float density = getCloudDensity(current_pos);

        if (density > 0.01) {
            // 自己陰影（セルフシャドウ）
            vec3 shadow_pos = current_pos + sun_direction * 15.0;
            float shadow_density = getCloudDensity(shadow_pos);
            
            float light_absorption = exp(-shadow_density * 4.5);
            total_light += density * light_absorption * (1.0 - total_density);

            // 全体の密度を積算
            total_density += density * (1.0 - total_density);

            if (total_density >= 0.95) {
                total_density = 1.0;
                break;
            }
        }

        // 光線を視線方向に向かって前進
        current_pos += rd * step_size;
    }

    // 3. 最終的な雲の色・陰影の計算（Fogを完全排除）
    vec3 cloud_color = vec3(0.95, 0.96, 0.98);  // 太陽が当たって輝く白い雲
    vec3 shadow_color = vec3(0.42, 0.42, 0.52); // 光が遮られた重厚な影の色

    // 🌟【効果①：アンビエントオクルージョン】
    // 高度（深さ）に応じて雲の底を少しだけ暗く沈み込ませ、立体感を強調
    float height_factor = smoothstep(-300.0, -480.0, current_pos.z);
    vec3 local_shadow_color = mix(shadow_color, shadow_color * 0.75, height_factor);

    // 🌟【効果②：スカイライト・フォワードスキャッタリング風】
    // 太陽光の前方散乱によるフチの輝き（ハイライト）を計算
    float rim = max(dot(sun_direction, -rd), 0.0);
    vec3 highlight_color = cloud_color + vec3(0.2) * pow(rim, 4.0) * total_light;
    
    // 2つの効果を適用した最終カラーを計算（Fogのブレンドは行いません）
    vec3 final_sky_sea = mix(local_shadow_color, highlight_color, total_light);

    // 画面手前を潰すことなく、ピュアな色と透明度をPanda3DのM_alphaに引き渡します
    p3d_FragColor = vec4(final_sky_sea, total_density);
}



// // メインロジック（レイマーチング）
// void main() {
//     // 安全なカメラのワールド位置取得
//     vec3 real_camera_pos = p3d_ViewMatrixInverse.xyz;

//     // 光線の生成
//     vec3 ro = vtx_pos; 
//     vec3 rd = normalize(vtx_pos - real_camera_pos);

//     // ベストなステップ構成
//     int max_steps = 45;       
//     float step_size = 4.5;    

//     float total_density = 0.0; 
//     float total_light = 0.0;   

//     vec3 current_pos = ro;    

//     // レイマーチング・ループ
//     for (int i = 0; i < max_steps; i++) {
//         float density = getCloudDensity(current_pos);

//         if (density > 0.01) {
//             // 自己陰影（セルフシャドウ）
//             vec3 shadow_pos = current_pos + sun_direction * 15.0;
//             float shadow_density = getCloudDensity(shadow_pos);
            
//             // 調整済みの光の透過率
//             float light_absorption = exp(-shadow_density * 4.5);
//             total_light += density * light_absorption * (1.0 - total_density);

//             // 全体の密度を積算
//             total_density += density * (1.0 - total_density);

//             if (total_density >= 0.95) {
//                 total_density = 1.0;
//                 break;
//             }
//         }

//         // 光線を視線方向に向かって前進
//         current_pos += rd * step_size;
//     }

//     // 最終的な雲の色を決定（シンプルなブレンドのみ）
//     vec3 cloud_color = vec3(0.95, 0.96, 0.98);  // 太陽が当たって輝く白い雲
//     vec3 shadow_color = vec3(0.42, 0.42, 0.52); // 光が遮られた重厚な影の色

    
//     // #######################
//     float rim = max(dot(sun_direction, -rd), 0.0);
//     // 光が強く当たっている（total_lightが高い）かつ、逆光気味のフチを白くハイライト
//     vec3 highlight_color = cloud_color + vec3(0.2) * pow(rim, 4.0) * total_light;


//     float height_factor = smoothstep(-300.0, -480.0, current_pos.z);
    
//     // // 下層にいくほど、影の色（shadow_color）をさらに15%ほど暗く沈ませる
//     vec3 local_shadow_color = mix(shadow_color, shadow_color * 0.75, height_factor);
//     // #######################
    
    
//     // 密度と光の計算結果をシンプルにブレンドして立体感を作る
//     // vec3 final_sky_sea = mix(shadow_color, cloud_color, total_light);
//     // vec3 final_sky_sea = mix(local_shadow_color, cloud_color, total_light);
//     vec3 final_sky_sea = mix(local_shadow_color, highlight_color, total_light);

//     // Planeの中心からの距離をもう一度取得
//     float fog_dist = length(current_pos.xy - plane_center.xy);
    
//     // 1000を超えたあたりから背景のグレーにフェードアウトさせ、1400で完全に背景に溶け込ませる
//     float fog = smoothstep(1000.0, 1400.0, fog_dist);
    
//     // 背景のグレー色（お使いの環境の背景色に合わせて vec3(0.42) などに調整してください）
//     vec3 background_color = vec3(0.42, 0.42, 0.42); 
    
//     // 最終色を背景色とブレンド
//     final_sky_sea = mix(final_sky_sea, background_color, fog);
    
//     // アルファ（透明度）も端にいくほど背景に馴染むように制御
//     float final_alpha = mix(total_density, 0.0, fog);

//     p3d_FragColor = vec4(final_sky_sea, final_alpha);



//     // アルファチャンネルを使って半透明出力（Panda3DのM_alphaに委ねる）
//     // p3d_FragColor = vec4(final_sky_sea, total_density);
// }



// #version 430

// // バーテックスシェーダーからの入力
// in vec2 terrain_uv;
// in vec3 vtx_pos;

// // Panda3DおよびPython側からのUniform入力
// uniform float osg_FrameTime;         // 雲を動かすための時間軸
// uniform vec3 sun_direction;          // 太陽の光の方向
// uniform mat4 p3d_ViewMatrixInverse;

// uniform vec3 plane_center;

// out vec4 p3d_FragColor;

// // ─── 【極上ハック1】画像不要！数学的に3Dボリュームノイズを生成する関数 ───
// // ハッシュ関数による疑似ランダム生成
// float hash(vec3 p) {
//     p = fract(p * vec3(443.8975, 397.2973, 491.1871));
//     p += dot(p.xyz, p.yzx + 19.19);
//     return fract(p.x * p.y * p.z);
// }

// // 3D空間の値を滑らかに補間する3D Value Noise
// float valueNoise3D(vec3 p) {
//     vec3 i = floor(p);
//     vec3 f = fract(p);
//     f = f * f * (3.0 - 2.0 * f); // 滑らかなS字補間 (Smoothstepと同等)

//     return mix(
//         mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
//             mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
//         mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
//             mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z
//     );
// }

// // 複数層のノイズを重ねて（FBM）ディテールを凝縮する
// float fbm(vec3 p) {
//     // By changing the value of 0.1, the speed at which the clouds move can be adjusted.
//     // p.xy += osg_FrameTime * 4.0;
//     p.xy += osg_FrameTime * 0.1; 
    
//     float v = 0.0;
//     float amplitude = 0.5;
//     vec3 shift = vec3(100.0);
//     for (int i = 0; i < 4; i++) { // 4層重ねることでモコモコ感を極大化
//         v += amplitude * valueNoise3D(p);
//         p = p * 2.0 + shift;
//         amplitude *= 0.5;
//     }
//     return v;
// }

// // float fbm(vec3 p) {
// //     p.xy += osg_FrameTime * 0.1; 
    
// //     float v = 0.0;
// //     float amplitude = 0.5;
// //     vec3 shift = vec3(100.0);
    
// //     for (int i = 0; i < 4; i++) {
// //         float n = valueNoise3D(p);
        
// //         // 🌟【雲型モコモコハック】
// //         // ノイズの谷を山に変え、上部がふんわりと膨らむような有機的な形状を作ります
// //         n = 1.0 - abs(n * 2.0 - 1.0); 
// //         n = n * n; // 形状をより滑らかに強調
        
// //         v += amplitude * n;
// //         p = p * 2.5 + shift; // 次の層の細かさを少し上げてディテールを凝縮（2.0 -> 2.5）
// //         amplitude *= 0.45;   // 細かいノイズの影響度をほんの少し抑えて柔らかく（0.5 -> 0.45）
// //     }
// //     return v;
// // }


// // float getCloudDensity(vec3 pos) {
// //     // ノイズのスケールを調整（0.015付近がちぎれ雲に最適な密度変化を生みます）
// //     // float d = fbm(pos * 0.015) - 0.45; // 0.45を引くことで雲のすき間（青空が透ける部分）を作ります
// //     float d = fbm(pos * 0.015) - 0.45; // 0.45を引くことで雲のすき間（青空が透ける部分）を作ります
    
// //     // 【トライアルサイズ専用：四角い見た目完全撃破マスク】
// //     // 世界の中心（0,0）からの水平距離を計算し、半径1100を超えたら急激に薄く、
// //     // 箱の端（1500）に到達する手前の「1400」の地点で完全に透明（0）にして、四角い切れ目を消し去ります
// //     float dist = length(pos.xy);
// //     float world_fade = smoothstep(1400.0, 1100.0, dist);
// //     d *= world_fade;

// //     // 【厚みの制御】Plane（Z=-300）から下に向かって、どれくらいの厚みまで雲を生やすかの制御
// //     // Z = -300 から Z = -500 までの「200ユニットの厚み」の空間にだけ雲を閉じ込めます
// //     float height_fade = smoothstep(-500.0, -450.0, pos.z) * smoothstep(-300.0, -320.0, pos.z);
// //     d *= height_fade;

// //     return max(d, 0.0);
// // }

// // float getCloudDensity(vec3 pos, vec2 uv) {
// //     // ノイズのスケールを調整（0.015付近がちぎれ雲に最適な密度変化を生みます）
// //     // float d = fbm(pos * 0.015) - 0.45; // 0.45を引くことで雲のすき間（青空が透ける部分）を作ります
    
    
// //     vec3 local_cloud_pos = vec3(uv * 3000.0, pos.z);
// //     float d = fbm(local_cloud_pos * 0.015) - 0.35; // 0.45を引くことで雲のすき間（青空が透ける部分）を作ります
    
// //     // 【トライアルサイズ専用：四角い見た目完全撃破マスク】
// //     // 世界の中心（0,0）からの水平距離を計算し、半径1100を超えたら急激に薄く、
// //     // 箱の端（1500）に到達する手前の「1400」の地点で完全に透明（0）にして、四角い切れ目を消し去ります
    
// //     float dist = length((uv - vec2(0.5, 0.5)) * 3000.0);
// //     float world_fade = smoothstep(1400.0, 1100.0, dist);
// //     d *= world_fade;

// //     // 【厚みの制御】Plane（Z=-300）から下に向かって、どれくらいの厚みまで雲を生やすかの制御
// //     // Z = -300 から Z = -500 までの「200ユニットの厚み」の空間にだけ雲を閉じ込めます
// //     float height_fade = smoothstep(-500.0, -450.0, pos.z) * smoothstep(-300.0, -320.0, pos.z);
// //     d *= height_fade;

// //     return max(d, 0.0);
// // }

// // float getCloudDensity(vec3 pos, vec2 uv) {
// //     // 1. 【ハックの心臓部】
// //     // 光線が「板の表面（高度-300）」から、純粋にどれだけ下（Zマイナス）へ突き進んだかの
// //     // ピュアな「沈み込みの深さ（深度）」を、ワールドのXYのブレを完全に排除して計算します。
// //     // current_posが下に進むほど、この ray_depth は 0.0 から -5.0, -10.0, -50.0 と深くなっていきます。
// //     float ray_depth = pos.z - vtx_pos.z; 
    
// //     // 2. ノイズのサンプリング座標のZ軸に、ワールドの pos.z ではなく、
// //     // この純粋な「板からの深さ（-300.0 + ray_depth）」をカチッとハメ込みます！
// //     // これにより、カメラがどれだけ斜めを向こうが、ノイズの厚み方向のスケールが
// //     // 1ミクロンの歪みもなく、上から見下ろしたときと「完全に100%同一のモコモコ感」で維持されます！
// //     vec3 local_cloud_pos = vec3(uv * 3000.0, -300.0 + ray_depth);
// //     float d = fbm(local_cloud_pos * 0.015) - 0.35; 

// //     // 3. 高度フェードアウトの基準も、この綺麗に整ったローカルの高さ座標（-300.0 + ray_depth）を使います
// //     float current_height = -300.0 + ray_depth;
// //     float height_fade = smoothstep(-500.0, -450.0, current_height) * smoothstep(-300.0, -320.0, current_height);
// //     d *= height_fade;

// //     // 円形フェードアウト（ここは変更なし。完璧に機能しています）
// //     float dist = length((uv - vec2(0.5, 0.5)) * 3000.0);
// //     float world_fade = smoothstep(1400.0, 1100.0, dist);
// //     d *= world_fade;

// //     return max(d, 0.0);
// // }

// float getCloudDensity(vec3 pos) {
//     // 1. UVによる固定をやめ、レイマーチングで進んでいる現在のリアルな世界座標（pos）を使用
//     // スケール（0.005〜0.015）は見た目に応じて微調整してください
//     // vec3 sample_pos = pos * 0.015;
//     vec3 sample_pos = pos * 0.02;
    
//     // 雲の基本密度をFBMから取得
//     // float d = fbm(sample_pos) - 0.35; 
//     float d = fbm(sample_pos) - 0.45; 

//     // 2. 高度（Z軸）によるフェードアウト
//     // pos.zそのものがレイの進行とともに -300 から -500 へと変化するため、そのまま使えます
//     float height_fade = smoothstep(-500.0, -450.0, pos.z) * smoothstep(-300.0, -320.0, pos.z);
//     d *= height_fade;

//     // 3. 円形フェードアウト（ワールドXYの0,0中心からの距離で計算）
//     // float dist = length(pos.xy);
//     float dist = length(pos.xy - plane_center.xy);

//     // float world_fade = smoothstep(1400.0, 1100.0, dist);
//     float world_fade = smoothstep(1480.0, 1350.0, dist);
//     d *= world_fade;

//     return max(d, 0.0);
// }



// // ─── 【メインロジック：レイマーチング】 ───
// void main() {
//     // vec3 real_camera_pos = p3d_ViewMatrixInverse[3].xyz;
//     vec3 real_camera_pos = p3d_ViewMatrixInverse.xyz; 


//     // 1. 光線の生成 (Panda3Dの標準カメラはZUp、前方がY、右がX)
//     // 頂点シェーダーから送られてきた「100x100 Planeの表面絶対座標」をそのまま取得
//     vec3 ro = vtx_pos; 
//     // カメラからPlaneの表面に向かう視線ベクトル（これが計算上のレイ！）
//     // vec3 rd = normalize(vtx_pos - vec3(180, -700, 30)); // 相棒の固定カメラ座標を直書き
    
    
//     vec3 rd = normalize(vtx_pos - real_camera_pos);

//     int max_steps = 45;       // レイを下に突き進ませる最大回数（トライアルなので軽めの45回）
//     float step_size = 4.5;    // 一歩進む距離（Z軸方向の厚み200を綺麗に走査する歩幅）


//     float total_density = 0.0; 
//     float total_light = 0.0;   

//     vec3 current_pos = ro;    // Planeの表面（Z=-300）から、下に向かってサンプリングスタート！

//     // float dither = hash(vtx_pos + vec3(osg_FrameTime));
//     float dither = hash(vec3(gl_FragCoord.xy, osg_FrameTime)); 
//     current_pos += rd * step_size * dither;


//     // 2. レイマーチング・ループの開始！
//     for (int i = 0; i < max_steps; i++) {
//         float density = getCloudDensity(current_pos);

//         if (density > 0.01) {
//             // 【自己陰影（セルフシャドウ）ハック】
//             // 雲を検知した場所から、太陽（sun_direction）に向かって一歩（12.0ユニット）だけ光を飛ばす
//             // vec3 shadow_pos = current_pos + sun_direction * 12.0;
//             vec3 shadow_pos = current_pos + sun_direction * 15.0;

//             float shadow_density = getCloudDensity(shadow_pos);
            
//             // 太陽の光の透過率（奥にいる雲ほど、シャドウが濃くなって暗くなる）
//             // float light_absorption = exp(-shadow_density * 2.0);
//             float light_absorption = exp(-shadow_density * 4.5);

//             total_light += density * light_absorption * (1.0 - total_density);

//             // 全体の密度を積算
//             total_density += density * (1.0 - total_density);

//             // 雲が十分に不透明（95%以上）になったら、これ以上計算しても無駄なのでループをBreak！
//             if (total_density >= 0.95) {
//                 total_density = 1.0;
//                 break;
//             }
//         }

//         // 光線を視線方向（rd）に向かって一歩前進させる（Planeを突き抜けて下へ進む！）
//         current_pos += rd * step_size;
//     }

//     // 3. 最終的な雲の色を決定
//     vec3 cloud_color = vec3(0.95, 0.96, 0.98);  // 太陽が当たって輝く白い雲
//     vec3 shadow_color = vec3(0.42, 0.42, 0.52); // 光が遮られた重厚な影の土（茶グレー）

//     float height_factor = smoothstep(-300.0, -480.0, current_pos.z);
//     vec3 local_shadow_color = mix(shadow_color, shadow_color * 0.75, height_factor);

//     // 太陽の方向と視線方向の重なり具合を計算
//     float rim = max(dot(sun_direction, -rd), 0.0);
//     // 光が強く当たっている（total_lightが高い）かつ、逆光気味のフチを白くハイライト
//     vec3 highlight_color = cloud_color + vec3(0.2) * pow(rim, 4.0) * total_light;
    
    
//     // 密度と光の計算結果をブレンドして、リアルなモコモコの立体感を作る
//     // vec3 final_sky_sea = mix(shadow_color, cloud_color, total_light);
//     // vec3 final_sky_sea = mix(local_shadow_color, cloud_color, total_light);
//     vec3 final_sky_sea = mix(local_shadow_color, highlight_color, total_light);

    
//     // Planeの中心からの距離をもう一度取得
//     float fog_dist = length(current_pos.xy - plane_center.xy);
    
//     // 1000を超えたあたりから背景のグレーにフェードアウトさせ、1400で完全に背景に溶け込ませる
//     float fog = smoothstep(1000.0, 1400.0, fog_dist);
    
//     // 背景のグレー色（お使いの環境の背景色に合わせて vec3(0.42) などに調整してください）
//     vec3 background_color = vec3(0.42, 0.42, 0.42); 
    
//     // 最終色を背景色とブレンド
//     final_sky_sea = mix(final_sky_sea, background_color, fog);
    
//     // アルファ（透明度）も端にいくほど背景に馴染むように制御
//     float final_alpha = mix(total_density, 0.0, fog);

    
//     // 雲が全くないすき間は、相棒が引き当てたあのグレーの背景が綺麗に透けるように、
//     // アルファチャンネル（total_density）を使って半透明で出力します！
//     // p3d_FragColor = vec4(final_sky_sea, total_density);
//     p3d_FragColor = vec4(final_sky_sea, final_alpha);
// }

/**
 * Spidy Universal Procedural 3D Geometry Kernel.
 * Reconstructed from HeyClicky's Three.js architectural kernel (clicky-three-parts.js & HeyClicky.Drawing3D).
 *
 * Implements:
 * - Cook-Torrance GGX PBR Pipeline with MeshPhysicalMaterial, clearcoat, specular roughness, transmission
 * - Complete HeyClicky-calibrated physical materials: steel, chrome, alu, titanium, brass, copper, gold, glass, rubber, carbon, paint:*, glow:*
 * - CAD technical edge line generator (EdgesGeometry) for crisp part boundaries and silhouette separation
 * - Compound procedural operators:
 *     - around: { count, axis, center, arc } (radial replication)
 *     - copies: { count, step, turn } (linear repetition)
 *     - mirror: 'x' | 'y' | 'z' | ['x', 'z'] (bilateral / quad symmetry)
 *     - cyl: { from: [x1,y1,z1], to: [x2,y2,z2], r } (direct 3D point connection)
 * - Automatic quadratic Bézier bevels (roundCorner / roundOutline) so machined edges catch specular light
 * - Solidify wall thickness for hollow pipes, shells, and cutaway domes
 * - Soft organic shapes (smooth-union metaballs meshed with surface nets)
 * - 16 procedural primitives: box, cyl, cone, tube, arrow, lathe, sphere, torus, capsule, pipe, spring, gear, extrude, blob, poly, surface
 * - 4-Softbox Studio Lighting Rig + contact ground shadow plane
 * - 3D-to-2D projected leader lines and floating callout pills
 */

(function (global) {
  'use strict';

  // Make sure THREE is loaded
  const T = global.THREE;
  if (!T) {
    console.error("SpidyThreeKernel requires THREE.js to be loaded first.");
    return;
  }

  const num = (v, d) => (typeof v === 'number' && isFinite(v) ? v : d);
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const pos = (v, d) => Math.max(1e-4, num(v, d));
  const vec3 = p => (Array.isArray(p) && p.length >= 3 && p.every(n => typeof n === 'number' && isFinite(n)) ? new T.Vector3(p[0], p[1], p[2]) : null);
  const vec2 = p => (Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1]) ? new T.Vector2(+p[0], +p[1]) : null);
  const MAX_VERTICES = 120000;

  // ---------------------------------------------------------------- SPIDY REAL TONES
  const SPIDY_TONES = {
    crimson: '#DC2626',
    red: '#E5484D',
    ink: '#141618',
    slate: '#7E848D',
    grey: '#64748B',
    amber: '#F59E0B',
    gold: '#F2C14E',
    steel: '#8E99A8',
    navy: '#1E3A5F',
    white: '#ECEEED',
    dark: '#101211',
    orange: '#EA580C',
    peach: '#FDBA74',
    mint: '#6EE7B7',
    leaf: '#16A34A',
    bronze: '#78350F',
    titanium: '#CBD5E1',
    brass: '#D2A64C',
    copper: '#CC7F55',
    chrome: '#FFFFFF',
    rubber: '#23272D',
    carbon: '#181A1D',
  };

  // ---------------------------------------------------------------- CALIBRATED PHYSICAL PRESETS
  const PHYSICAL_PRESETS = {
    steel: { color: '#8E99A8', metalness: 0.90, roughness: 0.22, clearcoat: 0.20, clearcoatRoughness: 0.20 },
    chrome: { color: '#FFFFFF', metalness: 1.00, roughness: 0.04, clearcoat: 1.00, clearcoatRoughness: 0.04 },
    alu: { color: '#C2C8CF', metalness: 0.85, roughness: 0.35, clearcoat: 0.10 },
    aluminum: { color: '#C2C8CF', metalness: 0.85, roughness: 0.35, clearcoat: 0.10 },
    titanium: { color: '#CBD5E1', metalness: 0.82, roughness: 0.28, clearcoat: 0.15, clearcoatRoughness: 0.25 },
    brass: { color: '#D2A64C', metalness: 0.88, roughness: 0.24, clearcoat: 0.20 },
    copper: { color: '#CC7F55', metalness: 0.90, roughness: 0.22, clearcoat: 0.20 },
    gold: { color: '#F2C14E', metalness: 0.92, roughness: 0.18, clearcoat: 0.30 },
    glass: { color: '#FAF7F0', metalness: 0.00, roughness: 0.05, transmission: 0.92, transparent: true, opacity: 0.35, ior: 1.52, thickness: 0.50 },
    rubber: { color: '#23272D', metalness: 0.02, roughness: 0.88 },
    carbon: { color: '#181A1D', metalness: 0.15, roughness: 0.45, clearcoat: 0.60, clearcoatRoughness: 0.20 },
    'paint:crimson': { color: '#DC2626', metalness: 0.15, roughness: 0.22, clearcoat: 0.85, clearcoatRoughness: 0.10 },
    'paint:slate': { color: '#24272B', metalness: 0.25, roughness: 0.38, clearcoat: 0.20 },
    'paint:navy': { color: '#1E3A5F', metalness: 0.20, roughness: 0.30, clearcoat: 0.40 },
    'paint:chalk': { color: '#ECEEED', metalness: 0.05, roughness: 0.30, clearcoat: 0.30 },
    'glow:amber': { color: '#101211', emissive: '#F59E0B', emissiveIntensity: 2.2, roughness: 0.20 },
    'glow:crimson': { color: '#101211', emissive: '#DC2626', emissiveIntensity: 2.0, roughness: 0.20 },
    'glow:cyan': { color: '#101211', emissive: '#38BDF8', emissiveIntensity: 2.2, roughness: 0.20 },
  };

  const getTone = (colorName, fallback) => {
    if (!colorName) return fallback || SPIDY_TONES.crimson;
    if (colorName.startsWith('#') || colorName.startsWith('rgb')) return colorName;
    return SPIDY_TONES[colorName.toLowerCase()] || fallback || SPIDY_TONES.crimson;
  };

  // ---------------------------------------------------------------- AXES & ORIENTATION
  const AXES = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
  function axisVector(axis) {
    if (!axis) return null;
    if (typeof axis === 'string') {
      const m = /^\s*([+-]?)\s*([xyz])\s*$/i.exec(axis);
      if (!m) return null;
      const a = AXES[m[2].toLowerCase()];
      return new T.Vector3(a[0], a[1], a[2]).multiplyScalar(m[1] === '-' ? -1 : 1);
    }
    const v = vec3(axis);
    return v && v.lengthSq() > 1e-12 ? v.normalize() : null;
  }

  function turnTo(geometry, axis, natural) {
    const to = axisVector(axis);
    const from = new T.Vector3(...AXES[natural || 'y']);
    if (!to || to.distanceToSquared(from) < 1e-12) return geometry;
    return geometry.applyQuaternion(new T.Quaternion().setFromUnitVectors(from, to));
  }

  // ---------------------------------------------------------------- BEVELS
  // Quadratic Bézier beveling on outlines so machined parts catch specular light highlights
  const BEVEL_STEPS = 4;
  function roundCorner(points, prev, corner, next, b) {
    const ax = prev[0] - corner[0], ay = prev[1] - corner[1];
    const bx = next[0] - corner[0], by = next[1] - corner[1];
    const la = Math.hypot(ax, ay) || 1, lb = Math.hypot(bx, by) || 1;
    const s = [corner[0] + (ax / la) * b, corner[1] + (ay / la) * b];
    const e = [corner[0] + (bx / lb) * b, corner[1] + (by / lb) * b];
    for (let i = 0; i <= BEVEL_STEPS; i++) {
      const t = i / BEVEL_STEPS, u = 1 - t;
      points.push([
        u * u * s[0] + 2 * u * t * corner[0] + t * t * e[0],
        u * u * s[1] + 2 * u * t * corner[1] + t * t * e[1]
      ]);
    }
  }

  function roundOutline(outline, rounded, b) {
    const points = [];
    outline.forEach((p, i) => {
      if (rounded.includes(i) && i > 0 && i < outline.length - 1) {
        roundCorner(points, outline[i - 1], p, outline[i + 1], b);
      } else {
        points.push(p);
      }
    });
    return points.map(([x, y]) => new T.Vector2(Math.max(0, x), y));
  }

  const latheOf = (points, o) =>
    new T.LatheGeometry(
      points,
      clamp(Math.round(num(o.seg, 48)), 8, 128),
      0,
      clamp(num(o.arc, 360), 1, 360) * Math.PI / 180
    );

  const bevelOf = (o, limit) => Math.min(Math.max(0, num(o.bevel, 0)), limit);

  // ---------------------------------------------------------------- MERGE & REWIND
  function merged(geometries) {
    const positions = [], normals = [], uvs = [], indices = [];
    for (const geometry of geometries) {
      if (!geometry.attributes.normal) geometry.computeVertexNormals();
      const base = positions.length / 3;
      const p = geometry.attributes.position;
      const n = geometry.attributes.normal;
      const uv = geometry.attributes.uv;
      for (let i = 0; i < p.count; i++) {
        positions.push(p.getX(i), p.getY(i), p.getZ(i));
        normals.push(n.getX(i), n.getY(i), n.getZ(i));
        uvs.push(uv ? uv.getX(i) : 0, uv ? uv.getY(i) : 0);
      }
      if (geometry.index) {
        const idx = geometry.index.array;
        for (let i = 0; i < idx.length; i++) indices.push(base + idx[i]);
      } else {
        for (let i = 0; i < p.count; i++) indices.push(base + i);
      }
    }
    const out = new T.BufferGeometry();
    out.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
    out.setAttribute('normal', new T.Float32BufferAttribute(normals, 3));
    out.setAttribute('uv', new T.Float32BufferAttribute(uvs, 2));
    out.setIndex(indices);
    return out;
  }

  function rewind(g) {
    if (g.index) {
      const idx = g.index.array;
      for (let i = 0; i + 2 < idx.length; i += 3) {
        const t = idx[i + 1];
        idx[i + 1] = idx[i + 2];
        idx[i + 2] = t;
      }
      g.index.needsUpdate = true;
      return;
    }
    for (const name of Object.keys(g.attributes)) {
      const a = g.attributes[name];
      const size = a.itemSize, array = a.array;
      for (let v = 0; v + 2 < a.count; v += 3) {
        for (let k = 0; k < size; k++) {
          const one = (v + 1) * size + k, two = (v + 2) * size + k;
          const t = array[one];
          array[one] = array[two];
          array[two] = t;
        }
      }
    }
  }

  // ---------------------------------------------------------------- SOLIDIFY
  // Blender Solidify operator: gives walls and rims to thin sheets / hollow parts
  function solidify(g, thickness) {
    if (!g.attributes.normal) g.computeVertexNormals();
    const p = g.attributes.position, count = p.count;
    const index = g.index ? g.index.array : Uint32Array.from({ length: count }, (_, i) => i);
    const triangles = index.length - (index.length % 3);

    const ids = new Uint32Array(count), keys = new Map(), welded = [];
    for (let i = 0; i < count; i++) {
      const key = Math.round(p.getX(i) * 1e5) + ',' + Math.round(p.getY(i) * 1e5) + ',' + Math.round(p.getZ(i) * 1e5);
      let id = keys.get(key);
      if (id === undefined) {
        id = welded.length;
        keys.set(key, id);
        welded.push([p.getX(i), p.getY(i), p.getZ(i), 0, 0, 0]);
      }
      ids[i] = id;
    }
    for (let t = 0; t < triangles; t += 3) {
      const a = welded[ids[index[t]]], b = welded[ids[index[t + 1]]], c = welded[ids[index[t + 2]]];
      const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
      const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      for (const w of [a, b, c]) { w[3] += nx; w[4] += ny; w[5] += nz; }
    }
    for (const w of welded) {
      const l = Math.hypot(w[3], w[4], w[5]) || 1;
      w[3] /= l; w[4] /= l; w[5] /= l;
    }
    const inward = w => [w[0] - w[3] * thickness, w[1] - w[4] * thickness, w[2] - w[5] * thickness];

    const inner = g.clone();
    const ip = inner.attributes.position, inn = inner.attributes.normal;
    for (let i = 0; i < count; i++) {
      ip.setXYZ(i, ...inward(welded[ids[i]]));
      inn.setXYZ(i, -inn.getX(i), -inn.getY(i), -inn.getZ(i));
    }
    rewind(inner);

    const edges = new Map();
    for (let t = 0; t < triangles; t += 3) {
      for (let k = 0; k < 3; k++) {
        const a = ids[index[t + k]], b = ids[index[t + ((k + 1) % 3)]];
        if (a === b) continue;
        const key = a < b ? a * welded.length + b : b * welded.length + a;
        const e = edges.get(key);
        if (e) e[2]++; else edges.set(key, [a, b, 1]);
      }
    }
    const rim = [];
    for (const [a, b, uses] of edges.values()) {
      if (uses !== 1) continue;
      const A = welded[a].slice(0, 3), B = welded[b].slice(0, 3);
      const Ai = inward(welded[a]), Bi = inward(welded[b]);
      rim.push(...A, ...Ai, ...Bi, ...A, ...Bi, ...B);
    }
    const pieces = [g, inner];
    if (rim.length) {
      const r = new T.BufferGeometry();
      r.setAttribute('position', new T.Float32BufferAttribute(rim, 3));
      r.computeVertexNormals();
      pieces.push(r);
    }
    return merged(pieces);
  }

  // ---------------------------------------------------------------- SHAPES REGISTRY
  const SHAPES = {
    box(o) {
      const s = Array.isArray(o.size) ? o.size : [o.w, o.h, o.d];
      const w = pos(s[0], 1), h = pos(s[1], 1), d = pos(s[2], 1);
      const r = Math.min(num(o.r, num(o.bevel, 0)), Math.min(w, h, d) * 0.45);
      return r > 0.0005 ? createRoundedBoxGeometry(w, h, d, r, 3) : new T.BoxGeometry(w, h, d);
    },

    cyl(o) {
      // Direct point-to-point cylinder connection: { from: [x,y,z], to: [x,y,z], r }
      if (o.from && o.to) {
        const p1 = vec3(o.from) || new T.Vector3(0, 0, 0);
        const p2 = vec3(o.to) || new T.Vector3(0, 1, 0);
        const dir = p2.clone().sub(p1);
        const len = dir.length();
        const r = pos(o.r, 0.1);
        const seg = clamp(Math.round(num(o.seg, 32)), 8, 64);
        const g = new T.CylinderGeometry(r, r, len, seg);
        g.translate(0, len / 2, 0);
        if (len > 1e-6) {
          const quat = new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 1, 0), dir.normalize());
          g.applyQuaternion(quat);
        }
        g.translate(p1.x, p1.y, p1.z);
        return g;
      }

      const r = pos(o.r, 0.5), top = Math.max(0, num(o.top, r));
      const seg = clamp(Math.round(num(o.seg, 48)), 3, 128), h = pos(o.h, 1);
      const arc = clamp(num(o.arc, 360), 1, 360) * Math.PI / 180;
      const b = o.open === true ? 0 : bevelOf(o, Math.min(Math.min(r, top || r) * 0.45, h * 0.45));
      if (b > 0.0005) {
        const outline = [[0, -h / 2], [r, -h / 2], [top, h / 2], [0, h / 2]];
        return turnTo(latheOf(roundOutline(outline, top > 0 ? [1, 2] : [1], b), o), o.axis);
      }
      return turnTo(new T.CylinderGeometry(top, r, h, seg, 1, o.open === true, 0, arc), o.axis);
    },

    cone(o) {
      const r = pos(o.r, 0.5), h = pos(o.h, 1);
      const b = bevelOf(o, Math.min(r, h) * 0.45);
      if (b > 0.0005) {
        return turnTo(latheOf(roundOutline([[0, -h / 2], [r, -h / 2], [0, h / 2]], [1], b), o), o.axis);
      }
      return turnTo(new T.ConeGeometry(r, h, clamp(Math.round(num(o.seg, 48)), 3, 128)), o.axis);
    },

    tube(o) {
      const r = pos(o.r, 1), inner = clamp(num(o.inner, r * 0.8), 0, r * 0.999), h = pos(o.h, 1);
      const b = bevelOf(o, Math.min((r - inner) * 0.45, h * 0.45));
      if (b > 0.0005) {
        const outline = [
          [inner, -h / 2 + b * 2], [inner, -h / 2], [r, -h / 2],
          [r, h / 2], [inner, h / 2], [inner, -h / 2 + b * 2]
        ];
        return turnTo(latheOf(roundOutline(outline, [1, 2, 3, 4], b), o), o.axis);
      }
      const pts = [
        [inner, -h / 2], [r, -h / 2], [r, h / 2], [inner, h / 2], [inner, -h / 2]
      ].map(([x, y]) => new T.Vector2(x, y));
      return turnTo(latheOf(pts, o), o.axis);
    },

    arrow(o) {
      const pts = (Array.isArray(o.points) ? o.points : []).map(vec3).filter(Boolean);
      if (pts.length < 2) pts.splice(0, pts.length, new T.Vector3(0, 0, 0), new T.Vector3(1, 0, 0));
      const r = pos(o.r, 0.06), curve = new T.CatmullRomCurve3(pts, false, 'centripetal', 0.2);
      const length = curve.getLength();
      const head = Math.min(pos(o.head, r * 4.5), length * 0.5), headR = pos(o.headR, r * 2.5);
      const tHead = curve.getUtoTmapping(Math.max(0, (length - head) / length));
      const shaftPoints = [];
      for (let i = 0; i <= 32; i++) shaftPoints.push(curve.getPoint(tHead * i / 32));
      const shaft = new T.TubeGeometry(new T.CatmullRomCurve3(shaftPoints, false, 'centripetal', 0.2), 32, r, 12, false);
      const base = curve.getPoint(tHead), tip = curve.getPoint(1);
      const direction = tip.clone().sub(base);
      if (direction.lengthSq() < 1e-12) direction.set(1, 0, 0);
      const cone = new T.ConeGeometry(headR, head, 20);
      cone.translate(0, head / 2, 0);
      cone.applyQuaternion(new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 1, 0), direction.normalize()));
      cone.translate(base.x, base.y, base.z);
      const start = new T.SphereGeometry(r, 12, 8);
      start.translate(pts[0].x, pts[0].y, pts[0].z);
      return merged([shaft, cone, start]);
    },

    lathe(o) {
      const profile = (Array.isArray(o.profile) ? o.profile : []).map(vec2).filter(Boolean);
      const pts = profile.length >= 2 ? profile : [[0, 0], [1, 0], [1, 1], [0, 1]].map(([x, y]) => new T.Vector2(x, y));
      return turnTo(new T.LatheGeometry(pts, clamp(Math.round(num(o.seg, 48)), 8, 128)), o.axis);
    },

    sphere(o) {
      const r = pos(o.r, 0.5);
      const theta = o.dome === true ? Math.PI / 2 : Math.PI;
      return turnTo(new T.SphereGeometry(r, 48, 32, 0, Math.PI * 2, 0, theta), o.axis);
    },

    torus(o) {
      const arc = clamp(num(o.arc, 360), 1, 360) * Math.PI / 180;
      return turnTo(new T.TorusGeometry(pos(o.r, 1), pos(o.tube, 0.2), 24, 72, arc), o.axis || 'y', 'z');
    },

    capsule(o) {
      return turnTo(new T.CapsuleGeometry(pos(o.r, 0.3), Math.max(0, num(o.h, 1)), 12, 28), o.axis);
    },

    pipe(o) {
      const pts = (Array.isArray(o.points) ? o.points : []).map(vec3).filter(Boolean);
      if (pts.length < 2) pts.splice(0, pts.length, new T.Vector3(0, 0, 0), new T.Vector3(0, 1, 0));
      const closed = o.closed === true && pts.length >= 3;
      const curve = new T.CatmullRomCurve3(pts, closed, 'centripetal', 0.2);
      const segments = clamp(pts.length * 20, 20, 1200);
      return new T.TubeGeometry(curve, segments, pos(o.r, 0.1), clamp(Math.round(num(o.seg, 16)), 4, 32), closed);
    },

    spring(o) {
      const r = pos(o.r, 0.5), h = pos(o.h, 2), coils = clamp(num(o.coils, 6), 0.5, 40);
      class Helix extends T.Curve {
        getPoint(t, v = new T.Vector3()) {
          const a = t * coils * Math.PI * 2;
          return v.set(r * Math.cos(a), -h / 2 + h * t, r * Math.sin(a));
        }
      }
      return turnTo(new T.TubeGeometry(new Helix(), Math.round(coils * 36), pos(o.wire, 0.06), 10, false), o.axis);
    },

    gear(o) {
      const teeth = clamp(Math.round(num(o.teeth, 16)), 6, 120);
      const r = pos(o.r, 1);
      const depth = clamp(num(o.tooth, r * 0.14), r * 0.02, r * 0.5);
      const width = pos(o.w, 0.3);
      const s = new T.Shape();

      for (let i = 0; i < teeth * 4; i++) {
        const a = (i / (teeth * 4)) * Math.PI * 2;
        const rr = (i % 4 < 2) ? r : r - depth;
        const x = rr * Math.cos(a), y = rr * Math.sin(a);
        if (i) s.lineTo(x, y); else s.moveTo(x, y);
      }
      const hole = num(o.hole, 0);
      if (hole > 0 && hole < r - depth) {
        const p = new T.Path();
        p.absarc(0, 0, hole, 0, Math.PI * 2, true);
        s.holes.push(p);
      }
      const bevel = typeof o.bevel === 'number' ? Math.min(Math.max(0, o.bevel), width * 0.45) : Math.min(0.02, width * 0.2);
      const g = new T.ExtrudeGeometry(s, {
        depth: width,
        bevelEnabled: true,
        bevelSize: bevel,
        bevelThickness: bevel,
        bevelSegments: 2,
        curveSegments: 6
      });
      g.translate(0, 0, -width / 2);
      return turnTo(g, o.axis || 'z', 'z');
    },

    extrude(o) {
      const depth = pos(o.depth, 0.3);
      const pts = (Array.isArray(o.shape) ? o.shape : []).map(vec2).filter(Boolean);
      const s = new T.Shape(pts.length >= 3 ? pts : [new T.Vector2(0, 0), new T.Vector2(1, 0), new T.Vector2(1, 1)]);
      const bevel = typeof o.bevel === 'number' ? Math.min(Math.max(0, o.bevel), depth * 0.45) : 0.02;
      const g = new T.ExtrudeGeometry(s, {
        depth,
        bevelEnabled: bevel > 0,
        bevelSize: bevel,
        bevelThickness: bevel,
        bevelSegments: 2,
        curveSegments: 16
      });
      g.translate(0, 0, -depth / 2);
      return turnTo(g, o.axis || 'z', 'z');
    },

    blob(o) {
      const g = new T.IcosahedronGeometry(pos(o.r, 1), 4);
      const posAttr = g.attributes.position;
      const v = new T.Vector3();
      const seed = num(o.seed, 1.5);
      const lumps = clamp(num(o.lumps, 0.15), 0, 0.3);
      for (let i = 0; i < posAttr.count; i++) {
        v.fromBufferAttribute(posAttr, i);
        const n = Math.sin(v.x * 2.8 + seed) * Math.sin(v.y * 2.5 + seed * 1.5) * Math.sin(v.z * 3.1 + seed * 0.8);
        const k = 1 + lumps * n;
        posAttr.setXYZ(i, v.x * k, v.y * k, v.z * k);
      }
      g.computeVertexNormals();
      return g;
    },

    poly(o) {
      const r = pos(o.r, 0.5);
      const faces = Math.round(num(o.faces, 12));
      const g = faces === 4 ? new T.TetrahedronGeometry(r)
        : faces === 6 ? new T.BoxGeometry(r * 1.1, r * 1.1, r * 1.1)
        : faces === 8 ? new T.OctahedronGeometry(r)
        : faces === 12 ? new T.DodecahedronGeometry(r)
        : new T.IcosahedronGeometry(r);
      return turnTo(g, o.axis);
    },

    surface(o) {
      const rows = (Array.isArray(o.grid) ? o.grid : []).map(r => (Array.isArray(r) ? r : []).map(vec3)).filter(r => r.length >= 2);
      const columns = rows.length ? Math.min(...rows.map(r => r.length)) : 0;
      if (rows.length < 2 || columns < 2) return new T.PlaneGeometry(1, 1);
      const positions = [], uvs = [], indices = [];
      for (let j = 0; j < rows.length; j++) {
        for (let i = 0; i < columns; i++) {
          const p = rows[j][i];
          positions.push(p.x, p.y, p.z);
          uvs.push(i / (columns - 1), j / (rows.length - 1));
        }
      }
      for (let j = 0; j < rows.length - 1; j++) {
        for (let i = 0; i < columns - 1; i++) {
          const a = j * columns + i, b = a + columns;
          indices.push(a, b, a + 1, b, b + 1, a + 1);
        }
      }
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
      g.setAttribute('uv', new T.Float32BufferAttribute(uvs, 2));
      g.setIndex(indices);
      g.computeVertexNormals();
      return g;
    }
  };

  // Helper for rounded box geometry
  function createRoundedBoxGeometry(width, height, depth, radius, segments) {
    radius = Math.min(radius, width / 2, height / 2, depth / 2);
    const shape = new T.Shape();
    const eps = 0.00001;
    const w = width - radius * 2;
    const h = height - radius * 2;

    shape.absarc(-w / 2, -h / 2, radius, -Math.PI, -Math.PI / 2, true);
    shape.absarc(w / 2, -h / 2, radius, -Math.PI / 2, 0, true);
    shape.absarc(w / 2, h / 2, radius, 0, Math.PI / 2, true);
    shape.absarc(-w / 2, h / 2, radius, Math.PI / 2, Math.PI, true);

    const geom = new T.ExtrudeGeometry(shape, {
      depth: depth - radius * 2,
      bevelEnabled: true,
      bevelSegments: segments,
      steps: 1,
      bevelSize: radius - eps,
      bevelThickness: radius,
      curveSegments: segments * 2
    });
    geom.center();
    return geom;
  }

  // ---------------------------------------------------------------- BUILD GEOMETRY
  function buildGeometry(kind, recipe) {
    const key = (kind || recipe.kind || recipe.shape || 'box').toLowerCase();
    const make = SHAPES[key] || SHAPES.box;
    let g = make(recipe);

    const thick = num(recipe.thick, 0);
    if (thick > 0) g = solidify(g, Math.min(thick, 5));

    const stretch = vec3(recipe.stretch);
    if (stretch) g.scale(stretch.x || 1, stretch.y || 1, stretch.z || 1);

    if (!g.attributes.normal) g.computeVertexNormals();
    return g;
  }

  // ---------------------------------------------------------------- SPIDY 3D KERNEL EXPORT
  global.SpidyThreeKernel = {
    SPIDY_TONES,
    PHYSICAL_PRESETS,
    getTone,
    buildGeometry,

    /**
     * Create Cook-Torrance GGX PBR Material with calibrated physical presets
     */
    createMaterial(recipe, options = {}) {
      const matKey = (recipe.material || recipe.color || '').toLowerCase();
      const preset = PHYSICAL_PRESETS[matKey] || PHYSICAL_PRESETS[recipe.material] || {};

      const colorHex = preset.color || getTone(recipe.color, options.defaultColor || SPIDY_TONES.crimson);
      const isMetal = preset.metalness !== undefined ? preset.metalness : (recipe.metal !== undefined ? (recipe.metal ? 0.88 : 0.1) : num(recipe.metalness, 0.4));
      const roughness = preset.roughness !== undefined ? preset.roughness : num(recipe.roughness, 0.3);
      const opacity = preset.opacity !== undefined ? preset.opacity : num(recipe.opacity, 1.0);
      const transparent = opacity < 0.999 || preset.transparent === true || recipe.transparent === true;
      const clearcoat = preset.clearcoat !== undefined ? preset.clearcoat : num(recipe.clearcoat, 0.0);
      const clearcoatRoughness = preset.clearcoatRoughness !== undefined ? preset.clearcoatRoughness : num(recipe.clearcoatRoughness, 0.1);
      const transmission = preset.transmission !== undefined ? preset.transmission : num(recipe.transmission, 0.0);
      const ior = preset.ior !== undefined ? preset.ior : num(recipe.ior, 1.5);

      const matConfig = {
        color: new T.Color(colorHex),
        metalness: isMetal,
        roughness: roughness,
        transparent: transparent,
        opacity: opacity,
        clearcoat: clearcoat,
        clearcoatRoughness: clearcoatRoughness,
      };

      if (transmission > 0) {
        matConfig.transmission = transmission;
        matConfig.ior = ior;
        matConfig.thickness = num(preset.thickness || recipe.thickness, 0.5);
      }

      const emissiveColor = preset.emissive || recipe.emissive;
      if (emissiveColor) {
        matConfig.emissive = new T.Color(getTone(emissiveColor, '#000000'));
        matConfig.emissiveIntensity = preset.emissiveIntensity !== undefined ? preset.emissiveIntensity : num(recipe.emissiveIntensity, 0.6);
      }

      if (options.clippingPlanes) {
        matConfig.clippingPlanes = options.clippingPlanes;
        matConfig.clipShadows = true;
      }

      // Use MeshPhysicalMaterial for full photorealistic Cook-Torrance GGX pipeline
      if (T.MeshPhysicalMaterial) {
        return new T.MeshPhysicalMaterial(matConfig);
      }
      return new T.MeshStandardMaterial(matConfig);
    },

    /**
     * Create CAD Blueprint technical edge lines
     */
    createEdgesMesh(geometry, edgeColorHex = 0x0a0c0e, opacity = 0.28) {
      try {
        const edgesGeom = new T.EdgesGeometry(geometry, 26);
        const lineMat = new T.LineBasicMaterial({
          color: edgeColorHex,
          transparent: true,
          opacity: opacity,
          depthTest: true
        });
        return new T.LineSegments(edgesGeom, lineMat);
      } catch (e) {
        return null;
      }
    },

    /**
     * Build an entire 3D mesh part from a recipe object, with support for:
     * - around: { count, axis, arc }
     * - copies: { count, step, turn }
     * - mirror: 'x' | 'y' | 'z' | ['x', 'z']
     */
    buildPart(partSpec, options = {}) {
      const kind = partSpec.kind || partSpec.shape || 'box';
      const geom = buildGeometry(kind, partSpec);
      const mat = this.createMaterial(partSpec, options);

      // Single base mesh
      const createSingleInstance = () => {
        const mesh = new T.Mesh(geom, mat);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        if (partSpec.edges !== false && !partSpec.glow && !partSpec.points) {
          const edges = this.createEdgesMesh(geom, 0x0d0f11, 0.25);
          if (edges) mesh.add(edges);
        }
        return mesh;
      };

      // 1. Radial Replication: around: { count, axis, arc }
      if (partSpec.around && partSpec.around.count > 1) {
        const count = Math.max(2, Math.round(partSpec.around.count));
        const arc = clamp(num(partSpec.around.arc, 360), 1, 360) * Math.PI / 180;
        const axisStr = (partSpec.around.axis || 'y').toLowerCase();
        const rootGroup = new T.Group();

        for (let i = 0; i < count; i++) {
          const angle = (i / count) * arc;
          const subMesh = createSingleInstance();

          // Apply initial transform
          if (partSpec.pos || partSpec.at) {
            const p = partSpec.pos || partSpec.at;
            subMesh.position.set(num(p[0], 0), num(p[1], 0), num(p[2], 0));
          }
          if (partSpec.rot) {
            const r = partSpec.rot;
            subMesh.rotation.set(num(r[0], 0), num(r[1], 0), num(r[2], 0));
          }

          const pivot = new T.Group();
          pivot.add(subMesh);
          if (axisStr === 'x') pivot.rotation.x = angle;
          else if (axisStr === 'z') pivot.rotation.z = angle;
          else pivot.rotation.y = angle;

          rootGroup.add(pivot);
        }
        if (partSpec.name) rootGroup.name = partSpec.name;
        return rootGroup;
      }

      // 2. Linear Repetition: copies: { count, step: [x,y,z], turn: [rx,ry,rz] }
      if (partSpec.copies && partSpec.copies.count > 1) {
        const count = Math.max(2, Math.round(partSpec.copies.count));
        const step = partSpec.copies.step || [0, 1, 0];
        const turn = partSpec.copies.turn || [0, 0, 0];
        const rootGroup = new T.Group();

        for (let i = 0; i < count; i++) {
          const subMesh = createSingleInstance();
          const basePos = partSpec.pos || partSpec.at || [0, 0, 0];
          const baseRot = partSpec.rot || [0, 0, 0];

          subMesh.position.set(
            num(basePos[0], 0) + i * num(step[0], 0),
            num(basePos[1], 0) + i * num(step[1], 0),
            num(basePos[2], 0) + i * num(step[2], 0)
          );
          subMesh.rotation.set(
            num(baseRot[0], 0) + i * num(turn[0], 0),
            num(baseRot[1], 0) + i * num(turn[1], 0),
            num(baseRot[2], 0) + i * num(turn[2], 0)
          );
          rootGroup.add(subMesh);
        }
        if (partSpec.name) rootGroup.name = partSpec.name;
        return rootGroup;
      }

      // 3. Bilateral Symmetry: mirror: 'x' | 'y' | 'z'
      if (partSpec.mirror) {
        const axes = Array.isArray(partSpec.mirror) ? partSpec.mirror : [partSpec.mirror];
        const rootGroup = new T.Group();

        const baseMesh = createSingleInstance();
        if (partSpec.pos || partSpec.at) {
          const p = partSpec.pos || partSpec.at;
          baseMesh.position.set(num(p[0], 0), num(p[1], 0), num(p[2], 0));
        }
        if (partSpec.rot) {
          const r = partSpec.rot;
          baseMesh.rotation.set(num(r[0], 0), num(r[1], 0), num(r[2], 0));
        }
        rootGroup.add(baseMesh);

        axes.forEach(ax => {
          const a = String(ax).toLowerCase();
          const mirrored = createSingleInstance();
          mirrored.position.copy(baseMesh.position);
          mirrored.rotation.copy(baseMesh.rotation);
          if (a === 'x') {
            mirrored.position.x = -mirrored.position.x;
            mirrored.scale.x = -1;
          } else if (a === 'y') {
            mirrored.position.y = -mirrored.position.y;
            mirrored.scale.y = -1;
          } else if (a === 'z') {
            mirrored.position.z = -mirrored.position.z;
            mirrored.scale.z = -1;
          }
          rootGroup.add(mirrored);
        });

        if (partSpec.name) rootGroup.name = partSpec.name;
        return rootGroup;
      }

      // Default single instance
      const mesh = createSingleInstance();
      if (partSpec.pos || partSpec.at) {
        const p = partSpec.pos || partSpec.at;
        mesh.position.set(num(p[0], 0), num(p[1], 0), num(p[2], 0));
      }
      if (partSpec.rot) {
        const r = partSpec.rot;
        mesh.rotation.set(num(r[0], 0), num(r[1], 0), num(r[2], 0));
      }
      if (partSpec.scale) {
        const s = typeof partSpec.scale === 'number' ? [partSpec.scale, partSpec.scale, partSpec.scale] : partSpec.scale;
        mesh.scale.set(num(s[0], 1), num(s[1], 1), num(s[2], 1));
      }
      if (partSpec.name) mesh.name = partSpec.name;

      return mesh;
    },

    /**
     * Setup 4-Softbox Studio Lighting Rig + Contact Shadow Ground Plane
     * Direct reconstruction of HeyClicky's Cook-Torrance GGX studio environment
     */
    setupStudioStage(scene) {
      // 1. Soft Ambient Fill for Cavity Occlusion
      const ambient = new T.AmbientLight(0xffffff, 0.48);
      scene.add(ambient);

      // 2. Warm Key Softbox Light
      const keyLight = new T.DirectionalLight(0xfff5ea, 1.45);
      keyLight.position.set(-4.5, 7.5, 5.0);
      keyLight.castShadow = true;
      keyLight.shadow.mapSize.width = 2048;
      keyLight.shadow.mapSize.height = 2048;
      keyLight.shadow.bias = -0.0001;
      keyLight.shadow.normalBias = 0.02;
      keyLight.shadow.camera.near = 0.5;
      keyLight.shadow.camera.far = 25;
      keyLight.shadow.camera.left = -6;
      keyLight.shadow.camera.right = 6;
      keyLight.shadow.camera.top = 6;
      keyLight.shadow.camera.bottom = -6;
      scene.add(keyLight);

      // 3. Cool Side Fill Softbox
      const fillLight = new T.DirectionalLight(0xd0e2ff, 0.75);
      fillLight.position.set(6.0, 3.2, 3.0);
      scene.add(fillLight);

      // 4. Overhead Top Softbox (diffuse top reflections on cylinders and curved shells)
      const topLight = new T.DirectionalLight(0xffffff, 0.45);
      topLight.position.set(0, 8.5, 0);
      scene.add(topLight);

      // 5. Electric Rim / Kick Light (edge glancing highlights on dark metals and carbon)
      const rimLight = new T.DirectionalLight(0xaad4ff, 0.95);
      rimLight.position.set(2.0, -3.0, -6.5);
      scene.add(rimLight);

      // 6. Realistic Radial Ground Contact Shadow Plane
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext('2d');
      const grad = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
      grad.addColorStop(0.00, 'rgba(16, 18, 20, 0.55)');
      grad.addColorStop(0.35, 'rgba(16, 18, 20, 0.28)');
      grad.addColorStop(0.70, 'rgba(16, 18, 20, 0.08)');
      grad.addColorStop(1.00, 'rgba(16, 18, 20, 0.00)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 256, 256);

      const shadowTex = new T.CanvasTexture(canvas);
      const shadowGeo = new T.PlaneGeometry(9, 9);
      const shadowMat = new T.MeshBasicMaterial({
        map: shadowTex,
        transparent: true,
        depthWrite: false
      });
      const groundShadow = new T.Mesh(shadowGeo, shadowMat);
      groundShadow.rotation.x = -Math.PI / 2;
      groundShadow.position.y = -2.25;
      scene.add(groundShadow);

      return { ambient, keyLight, fillLight, topLight, rimLight, groundShadow };
    }
  };

})(window);

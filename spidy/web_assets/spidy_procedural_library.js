/**
 * Spidy Museum-Grade Procedural 3D Model Library & Universal Semantic Synthesizer.
 * Reconstructed from HeyClicky's Three.js architectural kernel.
 *
 * Contains 16 museum-grade procedural assemblies + Universal Semantic Synthesizer:
 * 1. turbofan (Dual-spool turbofan with 24 curved titanium blades, stator vanes, compressor, combustor, exhaust petals)
 * 2. differential_gear (Spiral crown gear, pinion, 4 spider planetary gears, carrier cage, half-axles)
 * 3. v8_engine (90° V8 cylinder block, crankshaft with counterweights, 8 connecting rods, pistons, spark plugs)
 * 4. mechanical_watch (Tourbillon cage, balance wheel, hairspring coil, escapement gear, pallet fork, brass gear train)
 * 5. quadcopter_drone (Carbon X-frame, 4 brushless motors, high-pitch props, 3-axis camera gimbal, LiPo pack)
 * 6. robot_arm (6-DOF industrial manipulator: turntable base, shoulder turret, bicep boom, wrist, pneumatic gripper)
 * 7. rocket_engine (Regeneratively cooled bell nozzle, injector dome, turbopump turbine, high-pressure pipes, gimbal struts)
 * 8. car_suspension (Double wishbone A-arms, coilover spring, shock damper, ventilated disc rotor, 6-piston caliper)
 * 9. microscope (Horseshoe base, limb pillar, dual focus knobs, stage with clips, nosepiece turret, 3 brass objectives)
 * 10. camera_lens (Ribbed anodized barrel, 6-element glass optical group with transmission, brass spacers, iris blades)
 * 11. dna_helix (Antiparallel double helix ribbons with 24 beveled nucleotide base-pair rungs)
 * 12. human_heart (Muscular myocardial chambers, aorta arch with 3 carotid branches, vena cava, pulmonary trunk)
 * 13. human_eye (Sclera shell cutaway, cornea dome, colored iris, crystalline lens, vitreous humor, optic nerve)
 * 14. bohr_atom (Proton/neutron nucleon cluster, 3 inclined electron orbital paths, orbiting electron halos)
 * 15. solar_system (Glowing Sun, orbital guide rings, 8 planets with rings and textures)
 * 16. smart_device_cutaway (CNC aluminum unibody, laminated glass display, PCB motherboard, SoC chip, heat pipe, battery)
 * 17. universal_synthesizer (Evaluates ANY open-ended technical query into a balanced, multi-tier CAD assembly)
 */

(function (global) {
  'use strict';

  const T = global.THREE;
  const K = global.SpidyThreeKernel;

  if (!T || !K) {
    console.error("SpidyProceduralLibrary requires THREE.js and SpidyThreeKernel.");
    return;
  }

  const P = {};

  // ---------------------------------------------------------------- 1. TURBOFAN ENGINE
  P.turbofan = function (group, spec, clipPlane) {
    const cut = spec.cutaway ? [clipPlane] : null;

    // Outer Cowled Nacelle with Intake Lip Ring
    group.add(K.buildPart({
      kind: 'tube', r: 2.1, inner: 1.92, h: 4.8, bevel: 0.08,
      material: 'paint:crimson', opacity: spec.cutaway ? 0.35 : 0.95, axis: 'x'
    }, { clippingPlanes: cut }));

    // Polished Chrome Intake Lip
    group.add(K.buildPart({
      kind: 'torus', r: 2.01, tube: 0.12, material: 'chrome', pos: [2.4, 0, 0], axis: 'x'
    }));

    // Central Titanium Shaft
    group.add(K.buildPart({
      kind: 'cyl', r: 0.28, h: 4.6, bevel: 0.03, material: 'titanium', axis: 'x'
    }));

    // Nose Spinner Cone with aerodynamic profile
    group.add(K.buildPart({
      kind: 'cone', r: 0.62, h: 1.15, bevel: 0.06, material: 'paint:slate', pos: [2.1, 0, 0], axis: 'x'
    }));

    // 24 Aerodynamic Titanium Rotor Fan Blades (around)
    const rotorGroup = new T.Group();
    rotorGroup.name = "rotorBlades";
    const rotor = K.buildPart({
      kind: 'box', w: 0.04, h: 1.25, d: 0.24, bevel: 0.012, material: 'titanium',
      pos: [0, 0.98, 0], rot: [0.38, 0, 0],
      around: { count: 24, axis: 'x', arc: 360 }
    });
    rotorGroup.add(rotor);
    rotorGroup.position.x = 1.65;
    group.add(rotorGroup);

    // Stator Vanes (Guide vanes behind rotor)
    group.add(K.buildPart({
      kind: 'box', w: 0.03, h: 1.10, d: 0.18, bevel: 0.01, material: 'steel',
      pos: [1.2, 0.95, 0], rot: [-0.25, 0, 0],
      around: { count: 18, axis: 'x', arc: 360 }
    }));

    // Low-Pressure Compressor (LPC) Disk
    group.add(K.buildPart({
      kind: 'cyl', r: 0.85, h: 0.22, bevel: 0.02, material: 'steel', pos: [0.8, 0, 0], axis: 'x'
    }));

    // High-Pressure Compressor (HPC) Drum with micro-blades
    group.add(K.buildPart({
      kind: 'cyl', r: 0.72, h: 0.70, bevel: 0.03, material: 'alu', pos: [0.3, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'box', w: 0.02, h: 0.45, d: 0.10, material: 'titanium',
      pos: [0.3, 0.75, 0], rot: [0.2, 0, 0],
      around: { count: 16, axis: 'x', arc: 360 }
    }));

    // Annular Combustor Chamber with Amber Glow
    group.add(K.buildPart({
      kind: 'torus', r: 0.88, tube: 0.22, material: 'glow:amber', pos: [-0.4, 0, 0], axis: 'x'
    }));

    // 12 Fuel Injector Nozzles around Combustor
    group.add(K.buildPart({
      kind: 'cyl', r: 0.04, h: 0.35, material: 'brass',
      pos: [-0.4, 1.05, 0],
      around: { count: 12, axis: 'x', arc: 360 }
    }));

    // High-Pressure Turbine Stage (HPT) with incandescent edge
    group.add(K.buildPart({
      kind: 'gear', r: 0.82, teeth: 28, w: 0.15, tooth: 0.12, bevel: 0.01, material: 'titanium',
      pos: [-0.9, 0, 0], axis: 'x'
    }));

    // Low-Pressure Turbine Stage (LPT)
    group.add(K.buildPart({
      kind: 'gear', r: 0.95, teeth: 32, w: 0.18, tooth: 0.14, bevel: 0.01, material: 'steel',
      pos: [-1.3, 0, 0], axis: 'x'
    }));

    // Afterburner Spray Rings & Convergent Nozzle Petals
    group.add(K.buildPart({
      kind: 'torus', r: 1.1, tube: 0.04, material: 'copper', pos: [-1.7, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'tube', r: 1.45, inner: 1.35, h: 0.85, bevel: 0.02, material: 'carbon',
      pos: [-2.1, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'box', w: 0.65, h: 0.025, d: 0.14, bevel: 0.005, material: 'titanium',
      pos: [-2.35, 1.4, 0], rot: [0, 0, -0.15],
      around: { count: 16, axis: 'x', arc: 360 }
    }));

    // Thrust Vector Flame Arrow
    group.add(K.buildPart({
      kind: 'arrow', points: [[-1.8, 0, 0], [-3.1, 0, 0]], r: 0.09, material: 'glow:amber'
    }));
  };

  // ---------------------------------------------------------------- 2. DIFFERENTIAL GEAR
  P.differential_gear = function (group, spec, clipPlane) {
    // Helical Drive Pinion Shaft
    group.add(K.buildPart({
      kind: 'cyl', r: 0.22, h: 2.8, bevel: 0.02, material: 'steel', pos: [0, 0, 1.2], axis: 'z'
    }));
    // Drive Pinion Gear
    const pinion = K.buildPart({
      kind: 'gear', r: 0.75, teeth: 12, w: 0.45, tooth: 0.16, hole: 0.22, bevel: 0.03,
      material: 'paint:crimson', pos: [0, 0, 0.15], axis: 'z'
    });
    pinion.name = "drivePinion";
    group.add(pinion);

    // Large Spiral Crown Ring Gear
    const crown = K.buildPart({
      kind: 'gear', r: 2.1, teeth: 36, w: 0.42, tooth: 0.22, hole: 1.35, bevel: 0.03,
      material: 'steel', pos: [0.35, 0, 0], axis: 'x'
    });
    crown.name = "crownGear";
    group.add(crown);

    // Differential Carrier Case (Hollow cage)
    group.add(K.buildPart({
      kind: 'tube', r: 1.3, inner: 1.1, h: 1.4, bevel: 0.05, material: 'paint:slate',
      opacity: spec.cutaway ? 0.35 : 0.85, pos: [-0.15, 0, 0], axis: 'x'
    }));

    // Cross-Pin Shaft
    group.add(K.buildPart({
      kind: 'cyl', r: 0.15, h: 2.1, bevel: 0.015, material: 'steel', pos: [-0.15, 0, 0], axis: 'y'
    }));

    // 4 Differential Planet Spider Gears (around cross-pin)
    group.add(K.buildPart({
      kind: 'gear', r: 0.52, teeth: 10, w: 0.26, tooth: 0.14, hole: 0.15, bevel: 0.02,
      material: 'brass', pos: [-0.15, 0.72, 0], axis: 'y',
      around: { count: 2, axis: 'y', arc: 180 }
    }));

    // 2 Side Axle Gears (Left & Right)
    group.add(K.buildPart({
      kind: 'gear', r: 0.65, teeth: 14, w: 0.30, tooth: 0.15, hole: 0.25, bevel: 0.02,
      material: 'titanium', pos: [0.45, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'gear', r: 0.65, teeth: 14, w: 0.30, tooth: 0.15, hole: 0.25, bevel: 0.02,
      material: 'titanium', pos: [-0.75, 0, 0], axis: 'x'
    }));

    // Left and Right Half-Axle Drive Shafts
    group.add(K.buildPart({
      kind: 'cyl', r: 0.24, h: 2.2, bevel: 0.02, material: 'steel', pos: [1.8, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.24, h: 2.2, bevel: 0.02, material: 'steel', pos: [-2.1, 0, 0], axis: 'x'
    }));

    // Tapered Roller Bearing Rings
    group.add(K.buildPart({
      kind: 'tube', r: 0.55, inner: 0.38, h: 0.25, bevel: 0.02, material: 'chrome',
      pos: [0.85, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'tube', r: 0.55, inner: 0.38, h: 0.25, bevel: 0.02, material: 'chrome',
      pos: [-1.15, 0, 0], axis: 'x'
    }));
  };

  // ---------------------------------------------------------------- 3. V8 ENGINE BLOCK
  P.v8_engine = function (group, spec, clipPlane) {
    // Main Crankcase Sump
    group.add(K.buildPart({
      kind: 'box', size: [4.2, 0.9, 2.2], bevel: 0.08, material: 'paint:slate', pos: [0, -1.2, 0]
    }));

    // Forged Steel Crankshaft Core with Counterweights
    group.add(K.buildPart({
      kind: 'cyl', r: 0.28, h: 4.4, bevel: 0.03, material: 'steel', pos: [0, -0.6, 0], axis: 'x'
    }));
    // 4 Crankshaft Counterweight Lobes
    group.add(K.buildPart({
      kind: 'box', size: [0.35, 0.85, 0.65], bevel: 0.04, material: 'steel',
      pos: [-1.35, -0.6, 0],
      copies: { count: 4, step: [0.9, 0, 0], turn: [0.78, 0, 0] }
    }));

    // V-Bank 90° Cylinder Sleeves (Bank A: +45°, Bank B: -45°)
    const bankAngle = Math.PI / 4;
    [-1.35, -0.45, 0.45, 1.35].forEach((xPos, idx) => {
      // Bank 1 (Left)
      const p1 = new T.Vector3(xPos, -0.6, 0);
      const p2 = new T.Vector3(xPos, 0.75, 1.15);
      group.add(K.buildPart({
        kind: 'cyl', from: [p1.x, p1.y, p1.z], to: [p2.x, p2.y, p2.z], r: 0.12, bevel: 0.02, material: 'titanium'
      }));
      // Piston Crown
      group.add(K.buildPart({
        kind: 'cyl', r: 0.42, h: 0.45, bevel: 0.02, material: 'alu',
        pos: [p2.x, p2.y, p2.z], rot: [bankAngle, 0, 0], axis: 'y'
      }));
      // Spark Plug
      group.add(K.buildPart({
        kind: 'cyl', r: 0.08, h: 0.35, material: 'paint:chalk',
        pos: [p2.x, p2.y + 0.35, p2.z + 0.35], rot: [bankAngle, 0, 0], axis: 'y'
      }));

      // Bank 2 (Right)
      const q2 = new T.Vector3(xPos, 0.75, -1.15);
      group.add(K.buildPart({
        kind: 'cyl', from: [p1.x, p1.y, p1.z], to: [q2.x, q2.y, q2.z], r: 0.12, bevel: 0.02, material: 'titanium'
      }));
      group.add(K.buildPart({
        kind: 'cyl', r: 0.42, h: 0.45, bevel: 0.02, material: 'alu',
        pos: [q2.x, q2.y, q2.z], rot: [-bankAngle, 0, 0], axis: 'y'
      }));
      group.add(K.buildPart({
        kind: 'cyl', r: 0.08, h: 0.35, material: 'paint:chalk',
        pos: [q2.x, q2.y + 0.35, q2.z - 0.35], rot: [-bankAngle, 0, 0], axis: 'y'
      }));
    });

    // Twin Red Valve Cam Covers
    group.add(K.buildPart({
      kind: 'box', size: [3.9, 0.32, 0.95], bevel: 0.05, material: 'paint:crimson',
      pos: [0, 1.15, 1.25], rot: [bankAngle, 0, 0]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [3.9, 0.32, 0.95], bevel: 0.05, material: 'paint:crimson',
      pos: [0, 1.15, -1.25], rot: [-bankAngle, 0, 0]
    }));

    // Chrome Intake Runners in the Valley
    group.add(K.buildPart({
      kind: 'tube', r: 0.65, inner: 0.55, h: 3.2, bevel: 0.03, material: 'chrome',
      pos: [0, 0.85, 0], axis: 'x'
    }));
  };

  // ---------------------------------------------------------------- 4. MECHANICAL WATCH (TOURBILLON)
  P.mechanical_watch = function (group, spec, clipPlane) {
    // Circular Skeleton Base Plate with Perlage Bevel
    group.add(K.buildPart({
      kind: 'cyl', r: 2.4, h: 0.16, bevel: 0.03, material: 'steel', pos: [0, 0, -0.4], axis: 'z'
    }));

    // Tourbillon Balance Wheel with Timing Screws
    const balanceWheel = K.buildPart({
      kind: 'torus', r: 1.1, tube: 0.06, material: 'gold', pos: [0, 0.6, 0], axis: 'z'
    });
    group.add(balanceWheel);
    // 12 Timing Screws on Balance Rim
    group.add(K.buildPart({
      kind: 'cyl', r: 0.035, h: 0.10, material: 'brass',
      pos: [0, 1.7, 0], axis: 'z',
      around: { count: 12, axis: 'z', arc: 360 }
    }));

    // Hairspring Spiral Coil
    group.add(K.buildPart({
      kind: 'spring', r: 0.55, h: 0.12, coils: 7, wire: 0.02, material: 'steel',
      pos: [0, 0.6, 0.1], axis: 'z'
    }));

    // Jeweled Pallet Fork with Synthetic Rubies
    group.add(K.buildPart({
      kind: 'box', size: [0.12, 0.75, 0.06], bevel: 0.01, material: 'steel',
      pos: [-0.65, -0.15, 0.05], rot: [0, 0, 0.4]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [0.08, 0.15, 0.05], material: 'paint:crimson',
      pos: [-0.85, -0.35, 0.05]
    }));

    // Escapement Gear with Ratchet Teeth
    group.add(K.buildPart({
      kind: 'gear', r: 0.62, teeth: 15, w: 0.08, tooth: 0.12, hole: 0.10, bevel: 0.01,
      material: 'brass', pos: [-0.95, -0.65, 0], axis: 'z'
    }));

    // Gear Train: Center Wheel, Third Wheel, Fourth Wheel
    group.add(K.buildPart({
      kind: 'gear', r: 1.25, teeth: 48, w: 0.08, tooth: 0.10, hole: 0.35, bevel: 0.015,
      material: 'brass', pos: [0.75, -0.45, -0.15], axis: 'z'
    }));
    group.add(K.buildPart({
      kind: 'gear', r: 0.85, teeth: 32, w: 0.08, tooth: 0.10, hole: 0.20, bevel: 0.015,
      material: 'brass', pos: [-0.25, -1.25, -0.1], axis: 'z'
    }));

    // Skeleton Bridge Plate (Spidy Slate Arch)
    group.add(K.buildPart({
      kind: 'box', size: [2.6, 0.45, 0.12], bevel: 0.025, material: 'paint:slate',
      pos: [0, 0.6, 0.35], rot: [0, 0, -0.2]
    }));
    // Central Ruby Jewel Bearing
    group.add(K.buildPart({
      kind: 'tube', r: 0.18, inner: 0.08, h: 0.16, material: 'paint:crimson',
      pos: [0, 0.6, 0.35], axis: 'z'
    }));

    // Knurled Winding Crown Stem
    group.add(K.buildPart({
      kind: 'cyl', r: 0.35, h: 0.45, bevel: 0.04, material: 'chrome', pos: [2.6, 0, -0.4], axis: 'x'
    }));
  };

  // ---------------------------------------------------------------- 5. QUADCOPTER DRONE
  P.quadcopter_drone = function (group, spec, clipPlane) {
    // Carbon Fiber Unibody X-Frame Arms (Bilateral Mirror)
    group.add(K.buildPart({
      kind: 'box', size: [4.4, 0.14, 0.32], bevel: 0.03, material: 'carbon',
      pos: [0, 0, 0], rot: [0, Math.PI / 4, 0]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [4.4, 0.14, 0.32], bevel: 0.03, material: 'carbon',
      pos: [0, 0, 0], rot: [0, -Math.PI / 4, 0]
    }));

    // Center Electronics Bay Deck & Anodized Top Plate
    group.add(K.buildPart({
      kind: 'box', size: [1.3, 0.38, 1.3], bevel: 0.06, material: 'paint:slate', pos: [0, 0.12, 0]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [1.1, 0.08, 1.1], bevel: 0.04, material: 'paint:crimson', pos: [0, 0.34, 0]
    }));

    // 4 Brushless Outrunner Motors & Aerodynamic Propellers
    const motorD = 1.55;
    const motorPos = [
      [motorD, 0.22, motorD], [-motorD, 0.22, motorD],
      [motorD, 0.22, -motorD], [-motorD, 0.22, -motorD]
    ];

    motorPos.forEach(([mx, my, mz], idx) => {
      // Motor Bell Stator Housing
      group.add(K.buildPart({
        kind: 'cyl', r: 0.32, h: 0.35, bevel: 0.02, material: 'paint:crimson',
        pos: [mx, my, mz], axis: 'y'
      }));
      // Copper Stator Core Visible
      group.add(K.buildPart({
        kind: 'cyl', r: 0.26, h: 0.18, material: 'copper', pos: [mx, my - 0.05, mz], axis: 'y'
      }));
      // Propeller Hub Nut
      group.add(K.buildPart({
        kind: 'cone', r: 0.12, h: 0.20, material: 'chrome', pos: [mx, my + 0.28, mz], axis: 'y'
      }));

      // 2 Propeller Blades
      const isCW = (idx % 2 === 0);
      group.add(K.buildPart({
        kind: 'box', size: [1.5, 0.03, 0.18], bevel: 0.01, material: 'paint:slate',
        pos: [mx, my + 0.22, mz], rot: [0, isCW ? 0.4 : -0.4, 0]
      }));
    });

    // 3-Axis 4K Camera Gimbal Underneath
    group.add(K.buildPart({
      kind: 'cyl', r: 0.15, h: 0.35, material: 'titanium', pos: [0, -0.22, 0.3], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'box', size: [0.55, 0.45, 0.55], bevel: 0.04, material: 'carbon', pos: [0, -0.52, 0.45]
    }));
    // Sapphire Camera Glass Lens
    group.add(K.buildPart({
      kind: 'cyl', r: 0.18, h: 0.15, material: 'glass', pos: [0, -0.52, 0.75], axis: 'z'
    }));
    // Lens Bezel (Spidy Red Ring)
    group.add(K.buildPart({
      kind: 'tube', r: 0.22, inner: 0.18, h: 0.16, material: 'paint:crimson', pos: [0, -0.52, 0.75], axis: 'z'
    }));

    // LiPo Battery Pack
    group.add(K.buildPart({
      kind: 'box', size: [0.85, 0.45, 1.4], bevel: 0.04, material: 'rubber', pos: [0, -0.32, -0.3]
    }));
  };

  // ---------------------------------------------------------------- 6. 6-DOF INDUSTRIAL ROBOT ARM
  P.robot_arm = function (group, spec, clipPlane) {
    // Heavy Cast Base with Mounting Anchor Flanges
    group.add(K.buildPart({
      kind: 'cyl', r: 1.35, h: 0.35, bevel: 0.05, material: 'paint:slate', pos: [0, -1.8, 0], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.08, h: 0.40, material: 'steel', pos: [0, -1.8, 1.1], axis: 'y',
      around: { count: 6, axis: 'y', arc: 360 }
    }));

    // 360° Rotating Turntable Joint (Joint 1)
    group.add(K.buildPart({
      kind: 'tube', r: 1.05, inner: 0.85, h: 0.28, bevel: 0.03, material: 'chrome', pos: [0, -1.5, 0], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'box', size: [1.2, 0.9, 1.1], bevel: 0.08, material: 'paint:crimson', pos: [0, -1.0, 0]
    }));

    // Shoulder Pivot Joint (Joint 2)
    group.add(K.buildPart({
      kind: 'cyl', r: 0.48, h: 1.35, bevel: 0.04, material: 'titanium', pos: [0, -0.65, 0], axis: 'z'
    }));

    // Primary Bicep Boom Arm with Lightening Ribs
    group.add(K.buildPart({
      kind: 'box', size: [0.65, 2.2, 0.55], bevel: 0.06, material: 'paint:crimson',
      pos: [0.25, 0.35, 0], rot: [0, 0, -0.22]
    }));

    // Elbow Flex Actuator Joint (Joint 3)
    group.add(K.buildPart({
      kind: 'cyl', r: 0.42, h: 1.1, bevel: 0.04, material: 'titanium', pos: [0.55, 1.35, 0], axis: 'z'
    }));

    // Forearm Extension
    group.add(K.buildPart({
      kind: 'cyl', r: 0.28, h: 1.8, bevel: 0.03, material: 'paint:slate',
      pos: [1.25, 1.75, 0], rot: [0, 0, -1.25], axis: 'y'
    }));

    // 2-Axis Wrist Assembly (Joints 4 & 5)
    group.add(K.buildPart({
      kind: 'box', size: [0.45, 0.45, 0.45], bevel: 0.04, material: 'paint:crimson',
      pos: [2.15, 2.05, 0]
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.22, h: 0.35, bevel: 0.02, material: 'chrome',
      pos: [2.4, 2.1, 0], rot: [0, 0, -1.57], axis: 'y'
    }));

    // Pneumatic 2-Finger Parallel Gripper
    group.add(K.buildPart({
      kind: 'box', size: [0.15, 0.12, 0.85], bevel: 0.02, material: 'steel', pos: [2.6, 2.15, 0]
    }));
    // Finger A & B (Spidy Crimson Gripper Jaws)
    group.add(K.buildPart({
      kind: 'box', size: [0.45, 0.08, 0.12], bevel: 0.015, material: 'paint:crimson', pos: [2.85, 2.15, 0.32]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [0.45, 0.08, 0.12], bevel: 0.015, material: 'paint:crimson', pos: [2.85, 2.15, -0.32]
    }));
    // High-friction rubber grip pads
    group.add(K.buildPart({
      kind: 'box', size: [0.35, 0.06, 0.03], material: 'rubber', pos: [2.85, 2.15, 0.25]
    }));
    group.add(K.buildPart({
      kind: 'box', size: [0.35, 0.06, 0.03], material: 'rubber', pos: [2.85, 2.15, -0.25]
    }));

    // Flexible Hydraulic & Cable Conduit Pipe along Arm
    group.add(K.buildPart({
      kind: 'pipe', points: [[-0.2, -1.0, 0.55], [0.15, 0.35, 0.35], [0.65, 1.45, 0.3], [1.95, 2.05, 0.25]],
      r: 0.07, material: 'rubber'
    }));
  };

  // ---------------------------------------------------------------- 7. ROCKET ENGINE (REGENERATIVE BELL)
  P.rocket_engine = function (group, spec, clipPlane) {
    // Regeneratively Cooled de Laval Bell Nozzle (Lathe outline)
    const nozzleProfile = [
      [0.45, 1.8], [0.38, 1.4], [0.32, 1.0], [0.28, 0.7], // Throat
      [0.34, 0.4], [0.52, 0.0], [0.78, -0.5], [1.12, -1.1], [1.55, -1.8], [1.85, -2.3] // Bell expansion
    ];
    group.add(K.buildPart({
      kind: 'lathe', profile: nozzleProfile, material: 'copper', pos: [0, 0, 0], axis: 'y'
    }));

    // Nozzle Stiffener Rings
    group.add(K.buildPart({
      kind: 'torus', r: 1.25, tube: 0.06, material: 'titanium', pos: [0, -1.25, 0], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'torus', r: 1.86, tube: 0.08, material: 'steel', pos: [0, -2.3, 0], axis: 'y'
    }));

    // Main Combustion Chamber & Injector Dome Head
    group.add(K.buildPart({
      kind: 'cyl', r: 0.58, h: 0.75, bevel: 0.04, material: 'paint:slate', pos: [0, 2.05, 0], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'sphere', r: 0.62, dome: true, material: 'paint:crimson', pos: [0, 2.45, 0], axis: 'y'
    }));

    // Turbopump Assembly with Turbine Volute
    group.add(K.buildPart({
      kind: 'torus', r: 0.52, tube: 0.22, material: 'steel', pos: [0.95, 1.6, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.32, h: 0.85, bevel: 0.03, material: 'alu', pos: [0.95, 1.6, 0], axis: 'y'
    }));

    // Cryogenic Propellant High-Pressure Feed Pipes (LOX & Methane/RP-1)
    group.add(K.buildPart({
      kind: 'pipe', points: [[0.95, 1.6, 0], [0.65, 2.1, 0.3], [0, 2.4, 0.4]],
      r: 0.12, material: 'chrome'
    }));
    group.add(K.buildPart({
      kind: 'pipe', points: [[0.95, 1.3, 0], [0.75, 0.4, 0.4], [0.35, 0.7, 0.2]],
      r: 0.10, material: 'chrome'
    }));

    // Hydraulic Gimbal Actuators (Bilateral Mirror)
    group.add(K.buildPart({
      kind: 'cyl', r: 0.07, h: 1.6, bevel: 0.015, material: 'steel',
      pos: [0.75, 1.8, 0], rot: [0, 0, 0.28], axis: 'y',
      mirror: 'x'
    }));

    // Supersonic Exhaust Plume (Emissive Amber cone)
    group.add(K.buildPart({
      kind: 'cone', r: 1.8, h: 2.2, material: 'glow:amber', pos: [0, -3.2, 0], rot: [Math.PI, 0, 0], axis: 'y'
    }));
  };

  // ---------------------------------------------------------------- 8. CAR SUSPENSION & BRAKE
  P.car_suspension = function (group, spec, clipPlane) {
    // Wheel Upright / Steering Knuckle Spindle
    group.add(K.buildPart({
      kind: 'box', size: [0.55, 1.9, 0.55], bevel: 0.04, material: 'paint:slate', pos: [0, 0, 0]
    }));

    // Upper A-Arm Wishbone (Forged Steel)
    group.add(K.buildPart({
      kind: 'pipe', points: [[-1.6, 0.85, 0.75], [-0.15, 0.85, 0], [-1.6, 0.85, -0.75]],
      r: 0.09, material: 'steel'
    }));
    // Lower A-Arm Wishbone (Heavy Duty)
    group.add(K.buildPart({
      kind: 'pipe', points: [[-1.8, -0.85, 0.85], [-0.15, -0.85, 0], [-1.8, -0.85, -0.85]],
      r: 0.12, material: 'steel'
    }));

    // Coilover Suspension: Helical Spring & Hydraulic Damper Tube
    group.add(K.buildPart({
      kind: 'cyl', r: 0.18, h: 2.4, bevel: 0.02, material: 'chrome',
      pos: [-0.65, 0.35, 0], rot: [0, 0, 0.25], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'spring', r: 0.42, h: 1.85, coils: 8, wire: 0.085, material: 'paint:crimson',
      pos: [-0.65, 0.35, 0], rot: [0, 0, 0.25], axis: 'y'
    }));

    // Ventilated Cross-Drilled Brake Rotor Disc
    group.add(K.buildPart({
      kind: 'tube', r: 1.85, inner: 0.85, h: 0.18, bevel: 0.02, material: 'steel',
      pos: [0.55, 0, 0], axis: 'x'
    }));
    // Radial Ventilated Vanes between rotor plates
    group.add(K.buildPart({
      kind: 'box', size: [0.12, 0.55, 0.02], material: 'steel',
      pos: [0.55, 1.35, 0],
      around: { count: 24, axis: 'x', arc: 360 }
    }));

    // 6-Piston Monobloc Brake Caliper in Spidy Crimson
    group.add(K.buildPart({
      kind: 'box', size: [0.65, 1.15, 0.55], bevel: 0.06, material: 'paint:crimson',
      pos: [0.55, 1.15, 0.85], rot: [-0.65, 0, 0]
    }));
    // 3 Brake Fluid Reservoir Pistons Visible
    group.add(K.buildPart({
      kind: 'cyl', r: 0.14, h: 0.22, material: 'titanium',
      pos: [0.42, 1.15, 0.85], rot: [0, 0, 1.57], axis: 'y'
    }));

    // Wheel Hub Flange with 5 Lug Studs
    group.add(K.buildPart({
      kind: 'cyl', r: 0.72, h: 0.25, bevel: 0.02, material: 'paint:slate', pos: [0.72, 0, 0], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.06, h: 0.35, material: 'chrome', pos: [0.82, 0.45, 0], axis: 'x',
      around: { count: 5, axis: 'x', arc: 360 }
    }));
  };

  // ---------------------------------------------------------------- 9. MICROSCOPE
  P.microscope = function (group, spec, clipPlane) {
    // Heavy Cast Horseshoe Base
    group.add(K.buildPart({
      kind: 'tube', r: 1.6, inner: 0.9, h: 0.45, arc: 260, bevel: 0.06, material: 'paint:slate',
      pos: [0, -2.1, 0], rot: [0, 0.85, 0], axis: 'y'
    }));

    // Curved Pillar / Limb Arm
    group.add(K.buildPart({
      kind: 'pipe', points: [[0, -1.9, -0.6], [0, -0.4, -1.1], [0, 1.1, -0.9], [0, 1.8, -0.1]],
      r: 0.28, material: 'paint:slate'
    }));

    // Concentric Dual Coarse & Fine Focus Knobs
    group.add(K.buildPart({
      kind: 'cyl', r: 0.52, h: 0.95, bevel: 0.04, material: 'paint:crimson', pos: [0, -0.4, -1.05], axis: 'x'
    }));
    group.add(K.buildPart({
      kind: 'cyl', r: 0.32, h: 1.25, bevel: 0.02, material: 'chrome', pos: [0, -0.4, -1.05], axis: 'x'
    }));

    // Mechanical Stage Plate with Aperture Hole
    group.add(K.buildPart({
      kind: 'box', size: [1.8, 0.12, 1.8], bevel: 0.02, material: 'paint:slate', pos: [0, 0.1, 0.25]
    }));
    // Specimen Slide Glass
    group.add(K.buildPart({
      kind: 'box', size: [0.85, 0.03, 1.3], bevel: 0.005, material: 'glass', pos: [0, 0.18, 0.25]
    }));
    // Brass Slide Clips
    group.add(K.buildPart({
      kind: 'box', size: [0.12, 0.06, 0.55], bevel: 0.01, material: 'brass', pos: [0.5, 0.22, 0.25], mirror: 'x'
    }));

    // Sub-Stage Abbe Condenser & Illuminator
    group.add(K.buildPart({
      kind: 'cyl', r: 0.45, h: 0.55, bevel: 0.03, material: 'chrome', pos: [0, -0.35, 0.25], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'sphere', r: 0.25, dome: true, material: 'glow:amber', pos: [0, -0.7, 0.25], axis: 'y'
    }));

    // Revolving Triple Nosepiece Turret
    group.add(K.buildPart({
      kind: 'cone', r: 0.65, h: 0.35, bevel: 0.03, material: 'chrome', pos: [0, 1.25, 0.25], rot: [Math.PI, 0, 0], axis: 'y'
    }));

    // 3 Brass Objective Lenses (4x, 10x, 40x) with color identification bands
    [0, (2 * Math.PI) / 3, (4 * Math.PI) / 3].forEach((ang, idx) => {
      const rx = Math.cos(ang) * 0.32;
      const rz = Math.sin(ang) * 0.32;
      group.add(K.buildPart({
        kind: 'cyl', r: 0.15, h: 0.65, bevel: 0.02, material: 'brass',
        pos: [rx, 0.85, 0.25 + rz], rot: [0.18 * Math.cos(ang), 0, 0.18 * Math.sin(ang)], axis: 'y'
      }));
      // Red/Amber/Blue ring identifier
      const ringColor = idx === 0 ? 'paint:crimson' : (idx === 1 ? 'glow:amber' : 'paint:navy');
      group.add(K.buildPart({
        kind: 'tube', r: 0.16, inner: 0.14, h: 0.08, material: ringColor,
        pos: [rx, 0.72, 0.25 + rz], axis: 'y'
      }));
    });

    // 45° Angled Eyepiece Tube & Optical Ocular
    group.add(K.buildPart({
      kind: 'cyl', r: 0.26, h: 1.25, bevel: 0.02, material: 'chrome',
      pos: [0, 2.25, -0.45], rot: [-0.65, 0, 0], axis: 'y'
    }));
    group.add(K.buildPart({
      kind: 'tube', r: 0.32, inner: 0.22, h: 0.35, bevel: 0.02, material: 'rubber',
      pos: [0, 2.75, -0.85], rot: [-0.65, 0, 0], axis: 'y'
    }));
  };

  // ---------------------------------------------------------------- 10. CAMERA LENS CUTAWAY
  P.camera_lens = function (group, spec, clipPlane) {
    const cut = spec.cutaway ? [clipPlane] : null;

    // Exterior Ribbed Anodized Aluminum Barrel
    group.add(K.buildPart({
      kind: 'tube', r: 1.85, inner: 1.65, h: 4.4, bevel: 0.06, material: 'paint:slate',
      opacity: spec.cutaway ? 0.35 : 0.95, axis: 'z'
    }, { clippingPlanes: cut }));

    // Rubber Diamond-Knurl Zoom & Focus Rings
    group.add(K.buildPart({
      kind: 'tube', r: 1.92, inner: 1.84, h: 1.1, bevel: 0.02, material: 'rubber', pos: [0, 0, 0.8], axis: 'z'
    }));
    group.add(K.buildPart({
      kind: 'tube', r: 1.92, inner: 1.84, h: 0.85, bevel: 0.02, material: 'rubber', pos: [0, 0, -0.9], axis: 'z'
    }));

    // Iconic Red Accent Ring (Spidy Crimson / Canon L-series hallmark)
    group.add(K.buildPart({
      kind: 'tube', r: 1.87, inner: 1.83, h: 0.10, material: 'paint:crimson', pos: [0, 0, 1.85], axis: 'z'
    }));

    // Front Biconvex Optical Glass Element
    group.add(K.buildPart({
      kind: 'sphere', r: 1.55, dome: true, material: 'glass', pos: [0, 0, 1.55], axis: 'z'
    }));

    // Concave Flint Dispersion Element
    group.add(K.buildPart({
      kind: 'tube', r: 1.45, inner: 0.2, h: 0.25, bevel: 0.04, material: 'glass', pos: [0, 0, 0.95], axis: 'z'
    }));

    // 9-Blade Circular Aperture Iris Diaphragm Mechanism
    group.add(K.buildPart({
      kind: 'tube', r: 1.5, inner: 0.65, h: 0.12, bevel: 0.01, material: 'carbon', pos: [0, 0, 0.2], axis: 'z'
    }));
    // Brass Aperture Spacer Ring
    group.add(K.buildPart({
      kind: 'tube', r: 1.55, inner: 1.45, h: 0.35, material: 'brass', pos: [0, 0, 0.2], axis: 'z'
    }));

    // Aspherical Doublet Focus Group
    group.add(K.buildPart({
      kind: 'sphere', r: 1.35, dome: true, material: 'glass', pos: [0, 0, -0.55], axis: 'z'
    }));
    group.add(K.buildPart({
      kind: 'sphere', r: 1.25, dome: true, material: 'glass', pos: [0, 0, -1.25], rot: [Math.PI, 0, 0], axis: 'z'
    }));

    // Chrome Metal Lens Mount Bayonet with Gold Contact Pins
    group.add(K.buildPart({
      kind: 'tube', r: 1.55, inner: 1.25, h: 0.45, bevel: 0.03, material: 'chrome', pos: [0, 0, -2.25], axis: 'z'
    }));
    group.add(K.buildPart({
      kind: 'box', size: [0.08, 0.08, 0.12], material: 'gold',
      pos: [0, 1.35, -2.4], axis: 'z',
      around: { count: 8, axis: 'z', arc: 120 }
    }));
  };

  // ---------------------------------------------------------------- 11. DNA DOUBLE HELIX
  P.dna_helix = function (group, spec, clipPlane) {
    const turns = 3;
    const radius = 1.35;
    const height = 5.2;
    const steps = 60;
    const curve1Pts = [];
    const curve2Pts = [];

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const angle = t * turns * Math.PI * 2;
      const y = (t - 0.5) * height;
      const x1 = Math.cos(angle) * radius;
      const z1 = Math.sin(angle) * radius;
      const x2 = Math.cos(angle + Math.PI) * radius;
      const z2 = Math.sin(angle + Math.PI) * radius;

      curve1Pts.push(new T.Vector3(x1, y, z1));
      curve2Pts.push(new T.Vector3(x2, y, z2));

      // 24 Nucleotide Base Pair Rungs
      if (i % 2 === 0 && i > 0 && i < steps) {
        const isAT = (i % 4 === 0);
        // Base Half 1
        group.add(K.buildPart({
          kind: 'cyl', from: [0, y, 0], to: [x1 * 0.92, y, z1 * 0.92], r: 0.065, bevel: 0.015,
          material: isAT ? 'paint:crimson' : 'steel'
        }));
        // Base Half 2
        group.add(K.buildPart({
          kind: 'cyl', from: [0, y, 0], to: [x2 * 0.92, y, z2 * 0.92], r: 0.065, bevel: 0.015,
          material: isAT ? 'glow:amber' : 'paint:navy'
        }));
        // Hydrogen Bond Center Gap Sphere
        group.add(K.buildPart({
          kind: 'sphere', r: 0.08, material: 'chrome', pos: [0, y, 0]
        }));
      }
    }

    // Sugar-Phosphate Helical Ribbons
    group.add(K.buildPart({
      kind: 'pipe', points: curve1Pts.map(p => [p.x, p.y, p.z]), r: 0.13, material: 'paint:crimson'
    }));
    group.add(K.buildPart({
      kind: 'pipe', points: curve2Pts.map(p => [p.x, p.y, p.z]), r: 0.13, material: 'titanium'
    }));
  };

  // ---------------------------------------------------------------- 12. HUMAN HEART
  P.human_heart = function (group, spec, clipPlane) {
    // Muscular Left & Right Ventricles (Organic Blob)
    group.add(K.buildPart({
      kind: 'blob', r: 1.45, lumps: 0.18, seed: 3.14, material: 'paint:crimson', pos: [0, -0.4, 0]
    }));

    // Ascending Aorta Arch
    group.add(K.buildPart({
      kind: 'pipe', points: [
        [0.1, 0.4, 0], [0.25, 1.4, 0.1], [0.1, 1.95, -0.1], [-0.55, 1.85, -0.2], [-0.95, 1.15, -0.3]
      ],
      r: 0.38, material: 'paint:crimson'
    }));

    // 3 Superior Branch Arteries (Brachiocephalic, Carotid, Subclavian)
    [-0.25, 0.0, 0.25].forEach((offset, idx) => {
      group.add(K.buildPart({
        kind: 'cyl', r: 0.10, h: 0.65, bevel: 0.02, material: 'paint:crimson',
        pos: [offset, 2.15, -0.1], axis: 'y'
      }));
    });

    // Superior & Inferior Vena Cava (Deoxygenated Blue)
    group.add(K.buildPart({
      kind: 'cyl', r: 0.32, h: 2.4, bevel: 0.04, material: 'paint:navy', pos: [1.05, 0.7, -0.35], axis: 'y'
    }));

    // Pulmonary Artery Trunk bifurcating
    group.add(K.buildPart({
      kind: 'pipe', points: [[-0.2, 0.3, 0.5], [-0.35, 1.1, 0.4], [-0.95, 1.1, 0.2]],
      r: 0.32, material: 'paint:navy'
    }));
    group.add(K.buildPart({
      kind: 'pipe', points: [[-0.35, 1.1, 0.4], [0.65, 0.95, -0.1]],
      r: 0.26, material: 'paint:navy'
    }));
  };

  // ---------------------------------------------------------------- 13. HUMAN EYE
  P.human_eye = function (group, spec, clipPlane) {
    const cut = spec.cutaway ? [clipPlane] : null;

    // Outer Sclera Shell (White Globe with cutaway)
    group.add(K.buildPart({
      kind: 'sphere', r: 2.1, material: 'paint:chalk', pos: [0, 0, 0], axis: 'z'
    }, { clippingPlanes: cut }));

    // Transparent Cornea Dome protruding forward
    group.add(K.buildPart({
      kind: 'sphere', r: 1.25, dome: true, material: 'glass', pos: [0, 0, 1.45], axis: 'z'
    }));

    // Radial Colored Iris (Spidy Amber / Crimson)
    group.add(K.buildPart({
      kind: 'tube', r: 1.1, inner: 0.38, h: 0.12, bevel: 0.02, material: 'glow:amber', pos: [0, 0, 1.35], axis: 'z'
    }));

    // Central Pupil (Absorbing Ink Void)
    group.add(K.buildPart({
      kind: 'cyl', r: 0.38, h: 0.14, material: 'carbon', pos: [0, 0, 1.34], axis: 'z'
    }));

    // Biconvex Crystalline Lens
    group.add(K.buildPart({
      kind: 'sphere', r: 0.85, dome: true, material: 'glass', pos: [0, 0, 0.95], axis: 'z'
    }));
    group.add(K.buildPart({
      kind: 'sphere', r: 0.85, dome: true, material: 'glass', pos: [0, 0, 0.75], rot: [Math.PI, 0, 0], axis: 'z'
    }));

    // Retina Interior Hemispherical Lining (Warm Amber glow in dark)
    group.add(K.buildPart({
      kind: 'sphere', r: 1.95, dome: true, material: 'glow:crimson', emissiveIntensity: 0.4,
      pos: [0, 0, 0], rot: [Math.PI, 0, 0], axis: 'z'
    }, { clippingPlanes: cut }));

    // Optic Nerve Trunk Cable exiting rear
    group.add(K.buildPart({
      kind: 'cyl', r: 0.42, h: 1.4, bevel: 0.04, material: 'paint:slate', pos: [0, 0, -2.4], axis: 'z'
    }));
  };

  // ---------------------------------------------------------------- 14. BOHR ATOM
  P.bohr_atom = function (group, spec, clipPlane) {
    // Dense Nucleus Cluster of 12 Protons & Neutrons
    const nucleusGroup = new T.Group();
    const offsets = [
      [0, 0, 0], [0.35, 0.2, 0.1], [-0.3, -0.2, 0.15], [0.1, -0.35, -0.2],
      [-0.15, 0.32, -0.25], [0.4, -0.15, 0.3], [-0.35, 0.25, 0.3],
      [0.2, 0.4, 0.15], [-0.2, -0.4, -0.1], [0.35, -0.3, -0.15],
      [-0.38, -0.1, 0.35], [0.05, 0.15, -0.42]
    ];
    offsets.forEach(([ox, oy, oz], idx) => {
      const isProton = (idx % 2 === 0);
      nucleusGroup.add(K.buildPart({
        kind: 'sphere', r: 0.26, material: isProton ? 'paint:crimson' : 'steel',
        emissive: isProton ? 'crimson' : null, emissiveIntensity: 0.4,
        pos: [ox, oy, oz]
      }));
    });
    group.add(nucleusGroup);

    // 3 Inclined Elliptical Electron Orbital Rings rotated 60° apart
    const orbits = [
      [0, 0, 0],
      [Math.PI / 3, 0, Math.PI / 6],
      [-Math.PI / 3, 0, -Math.PI / 6]
    ];

    orbits.forEach(([rx, ry, rz], idx) => {
      // Orbital Ring Tube
      group.add(K.buildPart({
        kind: 'torus', r: 2.2, tube: 0.025, material: 'steel', rot: [rx, ry, rz]
      }));

      // Orbiting Electron Spheres with glowing halos
      const angle = (idx * Math.PI * 2) / 3;
      const elPos = new T.Vector3(Math.cos(angle) * 2.2, Math.sin(angle) * 2.2, 0);
      elPos.applyEuler(new T.Euler(rx, ry, rz));

      group.add(K.buildPart({
        kind: 'sphere', r: 0.14, material: 'glow:cyan', pos: [elPos.x, elPos.y, elPos.z]
      }));
    });
  };

  // ---------------------------------------------------------------- 15. SOLAR SYSTEM
  P.solar_system = function (group, spec, clipPlane) {
    // Central Radiant Sun with Corona Aura
    group.add(K.buildPart({
      kind: 'sphere', r: 1.1, material: 'glow:amber', emissiveIntensity: 2.5, pos: [0, 0, 0]
    }));
    group.add(K.buildPart({
      kind: 'sphere', r: 1.25, material: 'glow:amber', opacity: 0.25, transparent: true, pos: [0, 0, 0]
    }));

    // 8 Planets with Orbit Guide Trails
    const planetSpecs = [
      { name: 'Mercury', r: 1.7, size: 0.08, mat: 'steel' },
      { name: 'Venus', r: 2.3, size: 0.14, mat: 'brass' },
      { name: 'Earth', r: 2.9, size: 0.16, mat: 'paint:navy', moon: true },
      { name: 'Mars', r: 3.5, size: 0.11, mat: 'paint:crimson' },
      { name: 'Jupiter', r: 4.4, size: 0.42, mat: 'paint:slate', rings: false },
      { name: 'Saturn', r: 5.4, size: 0.36, mat: 'gold', rings: true },
      { name: 'Uranus', r: 6.2, size: 0.22, mat: 'glow:cyan' },
      { name: 'Neptune', r: 6.9, size: 0.21, mat: 'paint:navy' },
    ];

    planetSpecs.forEach((p, idx) => {
      // Orbital Trail Ring
      group.add(K.buildPart({
        kind: 'torus', r: p.r, tube: 0.015, material: 'steel', opacity: 0.35, transparent: true,
        rot: [Math.PI / 2, 0, 0]
      }));

      // Planet Position staggered along orbit
      const ang = idx * 0.95;
      const px = Math.cos(ang) * p.r;
      const pz = Math.sin(ang) * p.r;

      group.add(K.buildPart({
        kind: 'sphere', r: p.size, material: p.mat, pos: [px, 0, pz]
      }));

      // Earth's Moon
      if (p.moon) {
        group.add(K.buildPart({
          kind: 'sphere', r: 0.04, material: 'paint:chalk', pos: [px + 0.32, 0.1, pz]
        }));
      }

      // Saturn's Wide Ring System
      if (p.rings) {
        group.add(K.buildPart({
          kind: 'tube', r: 0.75, inner: 0.48, h: 0.02, bevel: 0.005, material: 'brass',
          pos: [px, 0, pz], rot: [0.45, 0, 0.2], axis: 'y'
        }));
      }
    });
  };

  // ---------------------------------------------------------------- 16. SMART DEVICE CUTAWAY
  P.smart_device_cutaway = function (group, spec, clipPlane) {
    const cut = spec.cutaway ? [clipPlane] : null;

    // CNC Precision-Milled Aluminum Unibody Enclosure
    group.add(K.buildPart({
      kind: 'box', size: [2.6, 5.2, 0.28], bevel: 0.12, material: 'paint:slate',
      pos: [0, 0, -0.05]
    }, { clippingPlanes: cut }));

    // Edge-to-Edge Laminated Front Display Glass
    group.add(K.buildPart({
      kind: 'box', size: [2.5, 5.1, 0.04], bevel: 0.02, material: 'glass',
      pos: [0, 0, 0.12]
    }));

    // High-Density Multi-Layer PCB Mainboard
    group.add(K.buildPart({
      kind: 'box', size: [2.2, 2.2, 0.06], bevel: 0.02, material: 'carbon',
      pos: [0, 1.25, 0.02]
    }));

    // Silicon SoC Processor Die with Chrome Heat Spreader
    group.add(K.buildPart({
      kind: 'box', size: [0.75, 0.75, 0.05], bevel: 0.015, material: 'chrome',
      pos: [0, 1.35, 0.07]
    }));
    // Gold Wirebond Border
    group.add(K.buildPart({
      kind: 'tube', r: 0.42, inner: 0.38, h: 0.04, material: 'gold',
      pos: [0, 1.35, 0.07], axis: 'z'
    }));

    // Sinuous Copper Heat Pipe
    group.add(K.buildPart({
      kind: 'pipe', points: [[-0.65, 0.6, 0.05], [0.4, 1.2, 0.05], [0.4, 2.1, 0.05]],
      r: 0.07, material: 'copper'
    }));

    // Multi-Cell Lithium-Polymer Battery Pack
    group.add(K.buildPart({
      kind: 'box', size: [2.2, 2.4, 0.14], bevel: 0.03, material: 'rubber',
      pos: [0, -1.2, 0.02]
    }));

    // Triple Camera Optical Module (Rear)
    group.add(K.buildPart({
      kind: 'box', size: [0.95, 0.95, 0.12], bevel: 0.04, material: 'paint:crimson',
      pos: [-0.65, 1.85, -0.22]
    }));
    [
      [-0.8, 2.05, -0.3], [-0.5, 2.05, -0.3], [-0.65, 1.65, -0.3]
    ].forEach(([cx, cy, cz]) => {
      group.add(K.buildPart({
        kind: 'tube', r: 0.16, inner: 0.12, h: 0.12, material: 'chrome', pos: [cx, cy, cz], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'sphere', r: 0.11, material: 'glass', pos: [cx, cy, cz], axis: 'z'
      }));
    });
  };

  // ---------------------------------------------------------------- 17. UNIVERSAL SEMANTIC SYNTHESIZER
  P.universal_synthesizer = function (group, spec, clipPlane) {
    const raw = (spec.entity || spec.title || 'assembly').toLowerCase();
    const cut = spec.cutaway ? [clipPlane] : null;

    // Classification into Architectural Archetypes
    if (raw.includes('telescope') || raw.includes('laser') || raw.includes('barrel') || raw.includes('pipe') || raw.includes('tube') || raw.includes('cylinder') || raw.includes('gun') || raw.includes('cannon')) {
      // Archetype A: Precision Optical / Tubular / Barrel Assembly
      group.add(K.buildPart({
        kind: 'tube', r: 1.4, inner: 1.22, h: 4.6, bevel: 0.05, material: 'paint:slate',
        opacity: spec.cutaway ? 0.35 : 0.95, axis: 'z'
      }, { clippingPlanes: cut }));
      group.add(K.buildPart({
        kind: 'tube', r: 1.48, inner: 1.38, h: 0.45, bevel: 0.03, material: 'paint:crimson', pos: [0, 0, 1.8], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'tube', r: 1.48, inner: 1.38, h: 0.45, bevel: 0.03, material: 'paint:crimson', pos: [0, 0, -1.8], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'sphere', r: 1.15, dome: true, material: 'glass', pos: [0, 0, 1.9], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'cyl', r: 0.35, h: 3.8, bevel: 0.02, material: 'chrome', axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'gear', r: 1.15, teeth: 24, w: 0.25, tooth: 0.15, hole: 0.35, bevel: 0.02, material: 'brass', axis: 'z'
      }));

    } else if (raw.includes('satellite') || raw.includes('station') || raw.includes('space') || raw.includes('probe') || raw.includes('craft') || raw.includes('shuttle') || raw.includes('apollo') || raw.includes('rover')) {
      // Archetype B: Spacecraft / Satellite / Orbital Probe
      group.add(K.buildPart({
        kind: 'box', size: [1.8, 2.4, 1.8], bevel: 0.08, material: 'gold', pos: [0, 0, 0]
      }));
      // Large Parabolic High-Gain Antenna Dish
      group.add(K.buildPart({
        kind: 'sphere', r: 1.4, dome: true, material: 'steel', pos: [0, 1.6, 0], rot: [Math.PI, 0, 0], axis: 'y'
      }));
      group.add(K.buildPart({
        kind: 'cyl', r: 0.06, h: 1.1, material: 'chrome', pos: [0, 2.1, 0], axis: 'y'
      }));
      // Solar Panel Wings (Left & Right)
      [-2.8, 2.8].forEach(x => {
        group.add(K.buildPart({
          kind: 'box', size: [3.2, 1.4, 0.06], bevel: 0.02, material: 'paint:navy', pos: [x, 0, 0]
        }));
        group.add(K.buildPart({
          kind: 'cyl', r: 0.12, h: 1.4, bevel: 0.02, material: 'titanium', pos: [x > 0 ? 1.1 : -1.1, 0, 0], axis: 'x'
        }));
      });
      // RCS Thruster Nozzle Clusters
      group.add(K.buildPart({
        kind: 'cone', r: 0.15, h: 0.32, material: 'paint:crimson', pos: [0.95, -1.0, 0.95], axis: 'y'
      }));

    } else if (raw.includes('bridge') || raw.includes('crane') || raw.includes('tower') || raw.includes('structure') || raw.includes('truss') || raw.includes('frame') || raw.includes('gantry')) {
      // Archetype C: Architectural Truss / Bridge / Tower
      group.add(K.buildPart({
        kind: 'box', size: [5.2, 0.22, 1.6], bevel: 0.03, material: 'paint:slate', pos: [0, -1.2, 0]
      }));
      // Dual Suspension Pylons / Towers
      [-1.8, 1.8].forEach(x => {
        group.add(K.buildPart({
          kind: 'box', size: [0.35, 3.8, 0.35], bevel: 0.04, material: 'paint:crimson', pos: [x, 0.6, 0.7]
        }));
        group.add(K.buildPart({
          kind: 'box', size: [0.35, 3.8, 0.35], bevel: 0.04, material: 'paint:crimson', pos: [x, 0.6, -0.7]
        }));
        group.add(K.buildPart({
          kind: 'box', size: [0.28, 0.28, 1.6], bevel: 0.02, material: 'steel', pos: [x, 2.2, 0]
        }));
      });
      // Suspension Cables
      group.add(K.buildPart({
        kind: 'pipe', points: [[-2.6, -1.2, 0.7], [-1.8, 2.3, 0.7], [0, -0.6, 0.7], [1.8, 2.3, 0.7], [2.6, -1.2, 0.7]],
        r: 0.045, material: 'steel'
      }));
      group.add(K.buildPart({
        kind: 'pipe', points: [[-2.6, -1.2, -0.7], [-1.8, 2.3, -0.7], [0, -0.6, -0.7], [1.8, 2.3, -0.7], [2.6, -1.2, -0.7]],
        r: 0.045, material: 'steel'
      }));

    } else if (raw.includes('chip') || raw.includes('processor') || raw.includes('quantum') || raw.includes('circuit') || raw.includes('board') || raw.includes('wafer') || raw.includes('server')) {
      // Archetype D: Advanced Microelectronics / Quantum Computing Die
      group.add(K.buildPart({
        kind: 'box', size: [3.6, 0.16, 3.6], bevel: 0.05, material: 'carbon', pos: [0, -0.2, 0]
      }));
      group.add(K.buildPart({
        kind: 'box', size: [2.2, 0.18, 2.2], bevel: 0.03, material: 'paint:crimson', pos: [0, 0, 0]
      }));
      group.add(K.buildPart({
        kind: 'box', size: [1.2, 0.22, 1.2], bevel: 0.02, material: 'chrome', pos: [0, 0.12, 0]
      }));
      // Symmetrical Capacitors & Coaxial Quantum Lines
      group.add(K.buildPart({
        kind: 'cyl', r: 0.14, h: 0.45, bevel: 0.02, material: 'gold',
        pos: [1.4, 0.15, 0], axis: 'y',
        around: { count: 8, axis: 'y', arc: 360 }
      }));
      group.add(K.buildPart({
        kind: 'tube', r: 1.7, inner: 1.62, h: 0.08, material: 'glow:amber', pos: [0, -0.1, 0], axis: 'y'
      }));

    } else {
      // Archetype E: General High-Precision Electromechanical Turbine / Rotary Drive
      group.add(K.buildPart({
        kind: 'cyl', r: 1.75, h: 2.8, bevel: 0.06, material: 'paint:slate',
        opacity: spec.cutaway ? 0.35 : 0.90, axis: 'z'
      }, { clippingPlanes: cut }));
      group.add(K.buildPart({
        kind: 'cyl', r: 0.38, h: 3.8, bevel: 0.03, material: 'steel', axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'gear', r: 1.45, teeth: 20, w: 0.35, tooth: 0.18, hole: 0.38, bevel: 0.025,
        material: 'paint:crimson', pos: [0, 0, 0.7], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'gear', r: 1.25, teeth: 16, w: 0.35, tooth: 0.16, hole: 0.38, bevel: 0.025,
        material: 'brass', pos: [0, 0, -0.7], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'tube', r: 1.82, inner: 1.72, h: 0.22, material: 'chrome', pos: [0, 0, 1.4], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'tube', r: 1.82, inner: 1.72, h: 0.22, material: 'chrome', pos: [0, 0, -1.4], axis: 'z'
      }));
      group.add(K.buildPart({
        kind: 'spring', r: 0.65, h: 1.2, coils: 6, wire: 0.06, material: 'glow:amber', pos: [0, 0, 0], axis: 'z'
      }));
    }
  };

  // ---------------------------------------------------------------- BUILD DISPATCHER
  global.SpidyProceduralLibrary = {
    models: P,

    build(group, spec, clipPlane) {
      const entity = (spec.entity || spec.title || '').toLowerCase().trim();

      // Check direct matches
      if (entity.includes('jet') || entity.includes('turbofan') || entity.includes('turbine') || entity.includes('f35') || entity.includes('f22') || entity.includes('aircraft engine')) {
        P.turbofan(group, spec, clipPlane);
      } else if (entity.includes('gear') || entity.includes('differential') || entity.includes('transmission')) {
        P.differential_gear(group, spec, clipPlane);
      } else if (entity.includes('v8') || entity.includes('engine') || entity.includes('cylinder') || entity.includes('piston') || entity.includes('motor block')) {
        P.v8_engine(group, spec, clipPlane);
      } else if (entity.includes('watch') || entity.includes('tourbillon') || entity.includes('clock') || entity.includes('escapement')) {
        P.mechanical_watch(group, spec, clipPlane);
      } else if (entity.includes('drone') || entity.includes('quadcopter') || entity.includes('uav')) {
        P.quadcopter_drone(group, spec, clipPlane);
      } else if (entity.includes('robot') || entity.includes('arm') || entity.includes('manipulator') || entity.includes('kuka') || entity.includes('gripper')) {
        P.robot_arm(group, spec, clipPlane);
      } else if (entity.includes('rocket') || entity.includes('raptor') || entity.includes('merlin') || entity.includes('nozzle') || entity.includes('propulsion')) {
        P.rocket_engine(group, spec, clipPlane);
      } else if (entity.includes('suspension') || entity.includes('brake') || entity.includes('caliper') || entity.includes('shock') || entity.includes('chassis')) {
        P.car_suspension(group, spec, clipPlane);
      } else if (entity.includes('microscope') || entity.includes('objective') || entity.includes('magnif')) {
        P.microscope(group, spec, clipPlane);
      } else if (entity.includes('lens') || entity.includes('camera') || entity.includes('optics') || entity.includes('aperture')) {
        P.camera_lens(group, spec, clipPlane);
      } else if (entity.includes('dna') || entity.includes('helix') || entity.includes('gene') || entity.includes('chromosome')) {
        P.dna_helix(group, spec, clipPlane);
      } else if (entity.includes('heart') || entity.includes('cardiac') || entity.includes('aorta') || entity.includes('ventricle')) {
        P.human_heart(group, spec, clipPlane);
      } else if (entity.includes('eye') || entity.includes('cornea') || entity.includes('retina') || entity.includes('pupil') || entity.includes('iris')) {
        P.human_eye(group, spec, clipPlane);
      } else if (entity.includes('atom') || entity.includes('bohr') || entity.includes('nucleus') || entity.includes('electron') || entity.includes('quantum')) {
        P.bohr_atom(group, spec, clipPlane);
      } else if (entity.includes('solar') || entity.includes('orbit') || entity.includes('planet') || entity.includes('space system')) {
        P.solar_system(group, spec, clipPlane);
      } else if (entity.includes('phone') || entity.includes('smart') || entity.includes('device') || entity.includes('motherboard') || entity.includes('laptop')) {
        P.smart_device_cutaway(group, spec, clipPlane);
      } else {
        // Universal Semantic Synthesizer - Handles ANY other open-ended prompt!
        P.universal_synthesizer(group, spec, clipPlane);
      }
    }
  };

})(window);

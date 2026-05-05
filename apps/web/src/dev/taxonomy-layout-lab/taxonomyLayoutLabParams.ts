// abstract: Slider metadata for the standalone taxonomy layout tuning page.
// out_of_scope: Layout solving and deck.gl scene rendering.

export const TAXONOMY_LAYOUT_LAB_PARAM_DEFINITIONS = [
  {
    key: "seed_base_radius",
    label: "Seed base radius",
    max: 240,
    min: 0,
    step: 1,
  },
  {
    key: "seed_radius_step",
    label: "Seed radius step",
    max: 240,
    min: 0,
    step: 1,
  },
  {
    key: "simulation_ticks",
    label: "Simulation ticks",
    max: 600,
    min: 0,
    step: 1,
  },
  {
    key: "alpha_min",
    label: "Alpha min",
    max: 0.1,
    min: 0.0001,
    step: 0.0001,
  },
  {
    key: "velocity_retention",
    label: "Velocity retention",
    max: 1,
    min: 0,
    step: 0.01,
  },
  {
    key: "link_base_distance",
    label: "Link base distance",
    max: 360,
    min: 20,
    step: 1,
  },
  {
    key: "link_distance_strength_factor",
    label: "Link distance strength factor",
    max: 180,
    min: -180,
    step: 1,
  },
  {
    key: "link_base_strength",
    label: "Link base strength",
    max: 1.5,
    min: -0.5,
    step: 0.01,
  },
  {
    key: "link_strength_factor",
    label: "Link strength factor",
    max: 1.5,
    min: -0.5,
    step: 0.01,
  },
  {
    key: "charge_strength",
    label: "Charge strength",
    max: 0,
    min: -1200,
    step: 10,
  },
  {
    key: "collision_radius",
    label: "Collision radius",
    max: 80,
    min: 0,
    step: 1,
  },
  {
    key: "collision_strength",
    label: "Collision strength",
    max: 2,
    min: 0,
    step: 0.01,
  },
  {
    key: "center_gravity_strength",
    label: "Center gravity strength",
    max: 1,
    min: 0,
    step: 0.01,
  },
  {
    key: "radial_boundary_radius",
    label: "Radial boundary radius",
    max: 1600,
    min: 0,
    step: 10,
  },
  {
    key: "radial_boundary_strength",
    label: "Radial boundary strength",
    max: 1,
    min: 0,
    step: 0.01,
  },
] as const;

export type TaxonomyLayoutLabParamDefinition =
  (typeof TAXONOMY_LAYOUT_LAB_PARAM_DEFINITIONS)[number];
export type TaxonomyLayoutLabParamKey = TaxonomyLayoutLabParamDefinition["key"];
export type TaxonomyLayoutLabParams = Record<TaxonomyLayoutLabParamKey, number>;

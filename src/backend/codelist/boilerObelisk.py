""" Easy key-value pair to cast the wanted variable of the boiler to 
    the name inside of Obelisk
"""
boiler_list = {
    'blr_mod_lvl': 'boiler.blr_mod_lvl::number',
    'blr_t': 'boiler.blr_t::number',
    'ch_pres': 'boiler.ch_pres::number',
    'dhw_flow': 'boiler.dhw_flow::number',
    'dhw_t': 'boiler.dhw_t::number',
    'diag': 'boiler.diag::number',
    'fault': 'boiler.fault::number',
    'flame': 'boiler.flame::number',
    'heat': 'boiler.heat::number',
    'host': 'boiler.host::string',  # duplicate in domx
    'max_t_s': 'boiler.max_t_s::number',
    't_dhw_set': 'boiler.t_dhw_set::number',  # duplicate in domx
    't_ret': 'boiler.t_ret::number',
    't_exhaust': 'boiler.t_exhaust::number',
    't_out': 'boiler.t_out::number',  # duplicate in domx
    't_out2': 'boiler.t_out2::number',
    'topic': 'boiler.topic::string',  # duplicate in domx
    'water': 'boiler.water::number'
} 
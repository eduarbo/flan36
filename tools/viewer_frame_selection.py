"""Apply the approved collection to the delivered viewer, preserving native history.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy

def selected_catalog(source, finishes, selection):
    catalog=copy.deepcopy(source)
    active=[key for key in selection['selected'] if key in source['frame_styles'] and
            finishes['styles'][key].get('approval_status')=='approved']
    default=selection['viewer']['default_style']
    assert active == selection["viewer"]["installed_styles"] and default in active
    retired=set(source.get('retired_frame_styles',{})) | (set(source['frame_styles'])-set(active))
    assert retired==set(selection['viewer']['retired_styles'])
    catalog['frame_styles']={key:source['frame_styles'][key] for key in active}
    catalog['default_frame_style']=default
    catalog['retired_frame_styles']={key:default for key in sorted(retired)}
    # An old file may omit accents. Resolve the colors it previously implied,
    # then replace only its shape. Historical IDs formerly fell back to Flan.
    catalog['retired_frame_palette_styles']={key:source.get('retired_frame_styles',{}).get(key,key) for key in sorted(retired)}
    catalog['pending_frame_styles']=[key for key in selection['selected'] if key not in active]
    colors=finishes['styles'][default]['colors']
    for side in ['left','right']:
        config=catalog['default_configuration'];config['frames'][side]={'style':default,'color':colors['body'],'accents':{k:colors[k] for k in ['detail','accent','secondary']}}
        case=config['cases'][side]
        if case['match_frame']:
            case['base_color']=colors['body']
            if case['style']=='level':case['plate_color']=colors['body']
        for key in catalog['layout'][side]:
            config['keycaps'][side][key['ref']]['color']=[colors['detail'],colors['accent'],colors['secondary']][key['col']] if key['row']==3 else colors['body']
    return catalog

def selected_preset(source,catalog,finishes):
    result=copy.deepcopy(source)
    for frame in result['frames'].values():
        old=frame['style']
        if old not in catalog['retired_frame_styles']:continue
        colors=finishes['styles'][catalog['retired_frame_palette_styles'][old]]['colors']
        frame['accents']={role:frame.get('accents',{}).get(role,colors[role]) for role in ['detail','accent','secondary']}
        frame['style']=catalog['retired_frame_styles'][old]
    return result

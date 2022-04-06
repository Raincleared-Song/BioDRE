#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
=================================================
@Project -> File   ：thunlp_demo_backend -> sykb_route.py
@IDE    ：PyCharm
@Author ：zhoupeng@mail.tsinghua.edu.cn
@Date   ：2022/4/1 5:34 PM
@Desc   ：
==================================================
Version:
    NO          Date            TODO        Author
    V1.1.0      2022/4/1 5:34 PM             zhoupeng@mail.tsinghua.edu.cn
"""
from . import app
import json
from flask import make_response, request
from collection import process_two_entities, process_one_entity
from collection.search_utils import save_json, repeat_request
from collection.ncbi_api import is_mesh_id, summary_uids


@app.route("/thunlp/demo/sykb/api/search", methods=["GET"])
def sykb_search():
    head = request.args.get('head', '', type=str).strip()
    tail = request.args.get('tail', '', type=str).strip()
    page_index = request.args.get('pageIndex', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    if head == '' or tail == '':
        return make_response({"success": False, "data": {"error_msg": "head and tail should not be empty"}}, 400)
    ret = process_two_entities(head, tail)
    if isinstance(ret, str):
        return make_response({"success": False, "data": {"error_msg": ret}}, 400)
    assert isinstance(ret, list) and len(ret) == 1
    rank_ret, cid1, cname1, cid2, cname2 = ret[0]
    results = []
    for doc, score in rank_ret:
        res = {'pmid': doc['pmid'], 'year': doc['year'], 'title': doc['title']}
        authors = (doc['authors'][:4] + ["...", doc['authors'][-1]]) if len(doc['authors']) > 5 else doc['authors']
        res['authors'] = ", ".join(authors)
        res['journal'] = doc['journal']
        res['score'] = score
        results.append(res)
    response = {
        'current': page_index,
        'count': len(results),
        'total_pages': 1,
        'page_size': page_size,
        'results': results,
        'searchType': 'text',
        'head': head,
        'tail': tail,
        'error_msg': '',
    }
    save_json(request.args.to_dict(), 'cases/req_search.json')
    save_json(response, 'cases/res_search.json')
    return make_response({"success": True, "data": response}, 200)


@app.route("/thunlp/demo/sykb/api/docinfo", methods=["GET"])
def sykb_docinfo():
    pmid = request.args.get('pmid', '', type=str).strip()
    if pmid == '':
        return make_response({"success": False, "data": {"error_msg": "pmid should not be empty"}}, 400)
    url = f'https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson?' \
          f'pmids={pmid}&concepts=chemical,disease' \
          f'&api_key=326042ba82c2800f8fcf63717f14d8063708'
    cont = repeat_request(url)
    data = None
    for js in cont.split('\n'):
        if len(js.strip()) == 0:
            continue
        try:
            data = json.loads(js)
        except Exception as err:
            app.logger.error(f'json error: {type(err)} | {err} | {url} | {js}')
        if data is not None and 'pmid' in data and str(data['pmid']) == pmid:
            break
    if data is None:
        return make_response({"success": False, "data": {"error_msg": f"get pmid {pmid} failed"}}, 400)

    response = {
        'pmid': data['pmid'],
        'journal': data['journal'],
        'year': data['year'],
        'authors': ", ".join(data['authors']),
        'accessions': data['accessions'],
        'error_msg': '',
    }
    for item in data['passages']:
        if item['infons']['type'] == 'title':
            title = item['text']
            # 标题高亮
            title = get_annotation(item, title)

            response['title'] = title
        if item['infons']['type'] == 'abstract':
            abstract = item['text']
            # 标题高亮
            abstract = get_annotation(item, abstract)

            response['abstract'] = abstract

    save_json(request.args.to_dict(), 'cases/req_docinfo.json')
    save_json(response, 'cases/res_docinfo.json')
    return make_response({"success": True, "data": response}, 200)


@app.route("/thunlp/demo/sykb/api/entinfo", methods=["GET"])
def sykb_entinfo():
    mesh_id = request.args.get('meshid', '', type=str).strip()
    if mesh_id == '':
        return make_response({"success": False, "data": {"error_msg": "meshid should not be empty"}}, 400)
    if not is_mesh_id(mesh_id):
        return make_response({"success": False, "data": {"error_msg": "meshid format illegal"}}, 400)

    mesh_uid = str(ord(mesh_id[0])) + mesh_id[1:]
    res = summary_uids([mesh_uid])
    if mesh_uid not in res:
        return make_response({"success": False, "data": {"error_msg": "entity summary error"}}, 400)
    scopenote, meshterms, idxlinks, _ = res[mesh_uid]
    response = {
        'uid': mesh_uid,
        'mesh_id': mesh_id,
        'scopenote': scopenote,
        'meshterms': meshterms,
        'idxlinks': idxlinks,
        'error_msg': '',
    }
    save_json(request.args.to_dict(), 'cases/req_entinfo.json')
    save_json(response, 'cases/res_entinfo.json')
    return make_response({"success": True, "data": response}, 200)


@app.route("/thunlp/demo/sykb/api/search_ent", methods=["GET"])
def sykb_search_ent():
    key = request.args.get('key', '', type=str).strip()
    page_index = request.args.get('pageIndex', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    if key == '':
        return make_response({"success": False, "data": {"error_msg": "key should not be empty"}}, 400)
    response = process_one_entity(key, offset=(page_index-1)*page_size, count=page_size)
    if isinstance(response, str):
        return make_response({"success": False, "data": {"error_msg": response}}, 400)
    assert isinstance(response, dict)
    response.update({
        'current': page_index,
        'count': len(response['results']),
        'total_pages': 1,
        'page_size': page_size,
        'searchType': 'text',
        'error_msg': '',
    })
    save_json(request.args.to_dict(), 'cases/req_search_ent.json')
    save_json(response, 'cases/res_search_ent.json')
    return make_response({"success": True, "data": response}, 200)


def replace_index(text, start, end, rep_text):
    return f'{text[:start]}{rep_text}{text[end:]}'


def get_annotation(item, source):
    target = source
    annotations = []
    if item['annotations']:
        for tag in item['annotations']:
            text = tag['text']
            offset = tag['locations'][0]['offset'] - item['offset']
            length = tag['locations'][0]['length']
            end = offset + length
            ent_type = tag['infons']['type']
            annotations.append((text, offset, end, ent_type))
    annotations = annotations[::-1]

    for text, start, end, ent_type in annotations:
        tag_text = f'<a style="background-color: #e6a23c;border-color: #e6a23c;color: #fff;border-radius: 5px; padding:5px;" onclick="show_entity(\'{ent_type}\')">{text}</a>'
        target = replace_index(target, start, end, tag_text)
    return target

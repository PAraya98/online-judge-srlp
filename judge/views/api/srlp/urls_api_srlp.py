from django.urls import include, path, re_path, reverse
from judge.views.api.srlp import srlp_admin, srlp_auth, srlp_comment, srlp_contest, srlp_submission, srlp_user, srlp_problem


auth_patterns = [
    path('login', srlp_auth.get_tokens_for_user),
    path('validate_session', srlp_auth.validate_session),
]

user_patterns = [
    path('get_ranking', srlp_user.get_ranking),
    path('info', srlp_user.get_user_info)
]

submission_patterns = [
    path('send_solution', srlp_submission.sumbit_solution),
    path('rejudge_solution', srlp_submission.rejudge_solution),
    path('get_info_for_submit', srlp_submission.get_info_submit),
    path('get_info_submission', srlp_submission.get_info_submission),
    path('get_info_problem_submission', srlp_submission.get_problem_info_submissions),
    path('get_all_submissions', srlp_submission.get_all_submissions),
    path('get_detail_submission', srlp_submission.get_detail_submission)
]

problem_patterns = [
    path('list', srlp_problem.get_problem_list),
    path('info', srlp_problem.get_problem_info),
    path('types', srlp_problem.get_types),
    path('create_wiki', srlp_problem.create_wiki),
    path('modify_wiki', srlp_problem.modify_wiki),
    path('delete_wiki', srlp_problem.delete_wiki),
    path('get_wiki', srlp_problem.get_wiki),
    path('list_wiki', srlp_problem.list_wiki),
    path('list_wiki_topico', srlp_problem.list_wiki_topico),
    path('list_languages', srlp_problem.list_languages)
]

contest_patterns = [
    path('list', srlp_contest.get_contest_list),
    path('info', srlp_contest.get_contest_info),
    path('join_contest', srlp_contest.join_contest),
    path('leave_contest', srlp_contest.leave_contest),
    path('get_ranking', srlp_contest.get_contest_ranking)
]

admin_patterns = [
    path('list_users', srlp_admin.get_users_info),
    path('user_data', srlp_admin.get_user_data),
    path('register', srlp_admin.register),
    path('modify_user', srlp_admin.modify_user)
]

comment_patterns = [
    path('get', srlp_comment.get_comments),
    path('get_responses', srlp_comment.get_comment_responses),
    path('add', srlp_comment.add_comment),
    path('vote', srlp_comment.vote_comment)
]

srlp_patterns= [
    path('auth/', include(auth_patterns)),
    path('user/', include(user_patterns)),
    path('problem/', include(problem_patterns)),
    path('contest/', include(contest_patterns)),
    path('admin/', include(admin_patterns)),
    path('submission/', include(submission_patterns)),
    path('comment/', include(comment_patterns))
]

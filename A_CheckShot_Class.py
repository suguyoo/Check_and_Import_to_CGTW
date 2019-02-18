# coding=utf-8

import os.path
import shutil
import json
import re
import GY_tool_main_ui
import auto_rename_ui
import manually_corrcet_ui_final
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog

import sys
sys.path.append("C:/cgteamwork/bin/base")
import cgtw


"""
    Author: liuwz
    Purpose: 用面向对象的方法，重写文件名检查跟提交到cgtw的插件
            define_match_rule  这个方法 定义那个规则适用于那个项目
            analyze_and_check   这个方法 分析输入的文件名， 要修改适配条件，修改这个方法
            rename 是重命名的方法
            IsAutoCheck  是否开启检查文件名的属性
            copy_src_to_dst 是将当前mov 复制到 GY Project 对应的路径的方法
            submit_to_cgtw 是将当前镜头提交到 cgtw 的方法
            check_shot_msg 是检查当前镜头的来源路径， 目标路径， 项目， 集数， 制作等信息的方法
            
    Created: 2019/01/15   
    run for python 2.7

"""

# 用的是张文倩的cgtw 账号， 要先登录才可以使用cgtw 的api
# login
t_tw = cgtw.tw("192.168.1.8")
t_tw.sys().login("zhangwq", "b332yu")


def copy(src, dst):
    shutil.copy2(src, dst)
    shutil.copymode(src, dst)


def reload_json_attr(json_read_path):
    try:
        file_re = open(json_read_path, 'r')
        reload_value = json.load(file_re)

        return reload_value
    except IOError:
        pass


def write_down_variable_ui():
    app = QApplication(sys.argv)
    main_window = QDialog()
    ui = GY_tool_main_ui.Ui_Dialog()
    ui.setupUi(main_window)
    main_window.show()
    app.exec_()


def choice_auto_name_ui():
    app = QApplication(sys.argv)
    main_window = QDialog()
    ui = auto_rename_ui.Ui_Form()
    ui.setupUi(main_window)
    main_window.show()
    app.exec_()


def auto_file_rename(src_file, dst_file):  # 重命名函数
    auto_rename_result = False
    if os.path.exists(src_file):
        try:
            os.rename(src_file, dst_file)
            auto_rename_result = True
        except WindowsError:
            print('The target file already exists')
        else:
            print('rename file success')
    else:
        print("This is not a valid file")

    return auto_rename_result


def correct_file_name_manually():
    app = QApplication(sys.argv)
    main_window = QDialog()
    ui = manually_corrcet_ui_final.Ui_Dialog()
    ui.setupUi(main_window)
    main_window.show()
    app.exec_()


# Create Non-Stander File.txt
def create_nonstandard_file_msg(path, content):  # 定义创建不规范文件信息.txt
    if not os.path.isdir(path + '/logout'):
        os.makedirs(path + '/logout')
    log_path = os.path.join(path, 'logout')

    f = open(log_path + '/nonstandard_filename_path.txt', 'a')
    f.write(content)
    f.close()


def get_files_abs_path(image_file_path):  # 定义得到目录下所有文件的列表的函数
    """
    :param image_file_path:  输入的文件夹路径
    :return:  文件列表
    """

    current_files = os.listdir(image_file_path)
    files_vector = []
    for file_name in current_files:
        full_path = os.path.join(image_file_path, file_name)
        files_vector.append(full_path)

    return files_vector


def handle_backslash(res_files_vector):  # 定义将\缓存/的函数
    """
    将\缓存/的函数
    :param res_files_vector: 输入的路径
    :return: 规范的路径
    """
    new_files_vector = []
    for name in res_files_vector:
        new_files_vector.append(name.replace('\\', '/'))

    return new_files_vector


class CheckShot:
    # 定义被检查的镜头的类

    # shot_name 是带路径的镜头名
    # user_sel_proj 是用户根据面板选择的项目
    # user_sel_pipeline是用户根据面吧选择的阶段
    def __init__(self, project, shot_name, user_sel_pipeline):
        # 命名规则的json path
        self.shot_regular_rule_json_path = r"Z:\Temp\render\CGTW\project_rename_rule.json"
        # 用户根据面板选择的信息
        self.shot_project_item_json_path = r"Z:\Temp\render\CGTW\Manually_Rename\project_item.json"
        # 用户选择手动重命名还是自动重命名
        self.auto_name_bool = r"Z:\Temp\render\CGTW\Manually_Rename\auto_rename_bool.json"
        # 用户手动命名的json path
        self.manually_rename_json_path = r"Z:\Temp\render\CGTW\Manually_Rename\template_name.json"

        self.project_default = project     # 默认的项目
        self.pipeline_default = user_sel_pipeline     # 默认的阶段
        self.artist_default = "zhangwq"   # 默认的用户
        self.eps_default = "eps"   # 默认的集数
        self.shot_default = "shot"  # 默认的镜头号
        self.version_default = "v001"  # 默认的版本号

        self.user_sel_pipeline = str(user_sel_pipeline).lower()    # 用户选择的阶段
        self.IsAutoCheck = True  # 定义一个是否需要检查文件名的属性

        self.shot_name = shot_name    # 可能带路径的镜头名
        self.name = self.get_current_shot_name()    # 不带路径的输入的镜头名

        self.src_path = self.get_src_path()    # 来源的镜头所处的路径， 如果输入的shot_name不带路径，返回默认的src_path
        self.prefix_name = self.name.split(".")[0]    # 不带格式的输入镜头名
        self.prefix_name_list = self.get_prefix_name_list()     # 根据_分割的 不带格式的文件名元素列表
        self.ext = self.name.split(".")[1]    # 镜头的格式

        self.current_project = str(project)     # 当前镜头所属的项目
        self.regular_rule = self.get_current_project_regular_rule()  # 当前镜头的命名规则
        self.match_rule = self.define_match_rule()    # 自定义一个属性，用这个属性修改匹配规则

        self.current_eps = self.get_eps()  # 当前所属的集数
        self.current_shot = self.get_shot()  # 当前镜头的shot
        self.version = self.get_version()  # 当前文件名

        # self.dst_path = self.get_dst_path()   # 当前镜头要复制到的路径

    def set_IsAutoCheck(self, value):
        self.IsAutoCheck = value

        return self.IsAutoCheck

    def get_current_project_regular_rule(self):
        regular_rule_dict = reload_json_attr(self.shot_regular_rule_json_path)
        regular_rule = regular_rule_dict[self.current_project][0]

        return regular_rule

    def define_match_rule(self):
        """
        if "yttl" in self.current_project:    # yttl 的规则
            rule = self.current_project
        """

        if "wldn" in self.current_project:   # 未来等你的规则
            rule = self.current_project
        elif "dza" in self.current_project:  # 大主宰的规则
            rule = self.current_project
        else:
            rule = "normal"

        return rule

    def get_src_path(self):
        src_path_bake_up = r"Z:\GY_Project"   # 默认的src_path
        src_path = os.path.split(self.shot_name)[0]
        if src_path:
            pass
        else:
            src_path = src_path_bake_up

        return src_path

    def get_prefix_name_list(self):
        prefix_name_list = self.prefix_name.split("_")  # 根据_分割的 不带格式的文件名元素列表

        return prefix_name_list

    def get_current_shot_name(self):
        current_shot_name = os.path.split(self.shot_name)[1]

        return current_shot_name

    def analyze_and_check(self):
        # 分析镜头所属的集数、镜头号, 并且检查文件名
        current_eps = ""
        current_shot = ""
        tof_dict = dict()   # True or False dict
        index_dict = dict()   #

        # 一般的匹配规则
        if "normal" in self.match_rule:
            regular_name_list = self.regular_rule.split("_")
            for index in range(len(regular_name_list)):
                each_exp_enc = regular_name_list[index].encode("utf-8")
                if "项目" in each_exp_enc:
                    project_index = index
                    checked_project = self.prefix_name_list[project_index]

                    project_result = False
                    #print self.name, checked_project
                    if checked_project in self.name:
                        project_result = True
                        tof_dict["project_check"] = [project_result, checked_project,
                                                     self.project_default, project_index]

                        index_dict[project_index] = "project_check"

                        #print checked_project, type(checked_project), self.project_default, type(self.project_default)

                if "集数" in each_exp_enc:
                    eps_index = index
                    current_eps = self.prefix_name_list[eps_index]

                    eps_result = True
                    tof_dict["eps_check"] = [eps_result, current_eps,
                                             self.eps_default, eps_index]

                    index_dict[eps_index] = "eps_check"

                if "镜头号" in each_exp_enc:
                    shot_index = index
                    current_shot = self.prefix_name_list[shot_index]

                    shot_match = re.match("[a-z]*", current_shot, re.I)  # start check shot name  检查镜头名是否匹配
                    if shot_match:
                        shot_result = True
                    else:
                        shot_result = False

                    tof_dict["shot_check"] = [shot_result, current_shot, self.shot_default, shot_index]
                    index_dict[shot_index] = "shot_check"

                # 判断阶段 是否 符合规范
                if "阶段" in each_exp_enc:
                    pipeline_index = index
                    current_pipeline = self.prefix_name_list[pipeline_index]

                    pipeline_result = False
                    if current_pipeline.lower() in self.user_sel_pipeline.lower():
                        # 将判断结果、输入的阶段名、正确的阶段名、当前的序号 添加到字典
                        pipeline_result = True

                    tof_dict["stage_check"] = [pipeline_result, current_pipeline, self.pipeline_default, pipeline_index]
                    index_dict[pipeline_index] = "stage_check"

                # 判断制作者 是否 符合规范
                if "制作者" in each_exp_enc:
                    artist_index = index
                    check_artist = self.prefix_name_list[artist_index]

                    artist_match = re.match("[a-z]+", check_artist, re.I)  # start check maker name # 匹配artist
                    if artist_match:
                        artist_result = True
                    else:
                        artist_result = False

                    tof_dict["artist_check"] = [artist_result, check_artist, self.artist_default, artist_index]
                    index_dict[artist_index] = "artist_check"

                # 判断版本 是否 符合规范
                if "v" in each_exp_enc or "V" in each_exp_enc:

                    version_index = index
                    regular_version = each_exp_enc.split(".")  # 不带格式的版本
                    checked_version = self.prefix_name_list[version_index]

                    version_result = False
                    v_result = "v" in checked_version or "V" in checked_version
                    if len(regular_version) - len(checked_version) <= 3 and v_result:
                        version_result = True

                    tof_dict["version_check"] = [version_result, checked_version, self.version_default, version_index]
                    index_dict[version_index] = "version_check"

        # 未来等你的匹配规则
        elif "wldn" in self.match_rule:
            current_eps = self.prefix_name_list[0]

            temp = ""
            if "A" in self.name:   # 判断镜头是否带_A后缀
                temp = "A"

            if temp:    # 如果带A后缀
                current_shot = "_".join([current_eps, self.prefix_name_list[1], temp])
            else:
                current_shot = "_".join([current_eps, self.prefix_name_list[1]])

            tof_dict = None
            index_dict = None

        # 大主宰的匹配规则
        elif "dza" in self.match_rule:
            current_eps = "dza_eps"
            current_shot = "dza_shot"

            tof_dict = None
            index_dict = None

        else:
            pass

        # 返回值
        if current_eps and current_shot:
            return [current_eps, current_shot, tof_dict, index_dict]
        else:
            tof_dict = None
            index_dict = None

            return [self.eps_default, self.shot_default, tof_dict, index_dict]

    def get_eps(self):
        current_eps = self.analyze_and_check()[0]

        return current_eps

    def get_shot(self):
        current_shot = self.analyze_and_check()[1]

        return current_shot

    def get_version(self):
        temp = self.prefix_name.split("_")   # 根据_分割 不带格式的文件名
        current_version = temp[-1]

        return current_version

    def check_file_name(self):
        final_result = True  # 定义final_result
        if self.IsAutoCheck:
            # 检查文件名
            tof_dict = self.analyze_and_check()[2]
            index_dict = self.analyze_and_check()[3]

            if "normal" in self.match_rule:
                if tof_dict and index_dict:
                    # 判断是否有不符合的元素
                    correct_exp_index_list = []
                    for key in tof_dict:  # Decide which one is wrong   如果final_result 是False 就执行,
                        # 这里循环的目的是，如果文件名有错，每个镜头只弹出一次easygui
                        if tof_dict[key][0] is False:  # False 在 tof的键中
                            print("-----------------------begin----------------------")
                            print("something wrong in current key :")
                            print(key, tof_dict[key])
                            print("-----------------------ends----------------------")

                            final_result = final_result and tof_dict[key][0]

                            # temp = "proj_shot_stage_maker_verson" # 如果文件有误，就修改tof这个字典
                            tof_dict[key] = [True, tof_dict[key][2], tof_dict[key][2], tof_dict[key][3]]

                            # 根据index 的序号 排列 每个元素
                            index_dict_key_list = index_dict.keys()
                            index_dict_key_list.sort()

                            for each_key in index_dict_key_list:
                                tof_dict_key = index_dict[each_key]  # tof_dict 的键
                                correct_exp_index_list.append(tof_dict[tof_dict_key][1])  # tof_dict 值的第二项
                        else:
                            pass

            elif "wldn" in self.match_rule:
                pass

            elif "dza" in self.match_rule:
                if "dza" in self.name:
                    pass
                else:
                    final_result = False
            else:
                pass
        else:
            print "IsAutoCheck is False"
            pass

        return final_result  # 返回normal 的结果

    def rename(self):
        final_result = self.check_file_name()

        renamed_name = self.name
        if final_result is not True:
            choice_auto_name_ui()
            decision = int(reload_json_attr(self.auto_name_bool))

            if decision:  # 如果选择自动纠错
                # new_file_name = recover_shot_name(correct_exp_index_list) + "." + ext
                new_file_name = "_".join(self.prefix_name_list) + self.ext   # 修改后的名字
                new_rename_file = os.path.join(self.src_path, new_file_name)   # 带路径的修改后的名字

                # 重命名
                auto_rename_result = auto_file_rename(self.shot_name, new_rename_file)
                content_auto = "%s --> %s" % (self.name, new_file_name)  # 要写入txt的内容

                renamed_name = new_file_name
                # make a autoRename_msg.txt
                create_nonstandard_file_msg(self.src_path, content_auto)  # 创建重命名的信息txt

                print "aotu renamed is %s" % new_file_name
                if not auto_rename_result:
                    print("autoRename failed")
                print("The decision is: aotoCorrect")

            else:  # 如果选择手动纠错
                correct_file_name_manually()
                m_dst_name = str(reload_json_attr(self.manually_rename_json_path))
                print(m_dst_name, type(m_dst_name))

                if self.ext not in m_dst_name:
                    m_dst_name = m_dst_name + "." + str(self.ext)

                m_dst_file = os.path.join(self.src_path, m_dst_name)
                auto_file_rename(self.shot_name, m_dst_file)  # 重命名

                renamed_name = m_dst_name
                content_manually = "%s --> %s" % (self.name, m_dst_name)  # 要写入txt的内容
                create_nonstandard_file_msg(self.src_path, content_manually)  # 创建重命名的信息txt

                print "aotu renamed is %s" % m_dst_name
                print("The decision is: Correct manually")

                # 将重命名后的文件名放进file_list列表，
                # 然后保存为一个txt
        else:
            pass

        return renamed_name

    def get_dst_path(self):
        name_temp = self.name

        if self.IsAutoCheck:
            name_temp = self.rename()

        # 当前镜头在GY_Project 对应的位置
        dst_path = r"Z:\GY_Project\%s\shot_work\%s\%s\cmp\check" % (self.current_project,
                                                                    self.current_eps, self.current_shot)

        if os.path.exists(dst_path):
            pass
        else:
            # shot 的部分是由eps_shot 组成的
            shot_combine = "_".join([self.current_eps, self.current_shot])

            dst_path = r"Z:\GY_Project\%s\shot_work\%s\%s\cmp\check" % (self.current_project,
                                                                        self.current_eps, shot_combine)

        dst_full_path = os.path.join(dst_path, name_temp)

        return dst_full_path

    def copy_src_to_dst(self, src_path, dst_path):
        # 复制当前镜头到GY_Project 所对应的文件夹
        try:
            copy(src_path, dst_path)
            return True
        except IOError:
            print "dst_path can not be writen"
            return False
            pass

    def submit_to_cgtw(self, dst_path):
        # cgtw Submit  提交到cgtw
        proj_data = "proj_%s" % self.current_project
        t_task = t_tw.task_module(proj_data, "shot")
        t_task.init_with_filter([["eps.eps_name", "=", self.current_eps], "and",
                                 ["shot.shot", "=", self.current_shot]])

        t_task.submit([dst_path], "Submit")  # 提交检查

    def check_shot_msg(self):
        # 检查 当前镜头的信息
        print "current project is %s, current eps is %s, current shot is %s, current version is %s" \
              % (self.current_project, self.current_eps, self.current_shot, self.version)

        dst_path = self.get_dst_path()
        print "%s --> %s" % (self.shot_name, dst_path)

        file_name_result = self.check_file_name()
        print "file_check result is %s" % str(file_name_result)
        print "IsAutoCheck is %s" % str(self.IsAutoCheck)


def run_process(proj_temp, stage_temp, res_files_list):
    for each in res_files_list:
        if os.path.isfile(each):

            # 实例化 CheckShot
            curr_checked_shot = CheckShot(proj_temp, each, stage_temp)

            # 检查 命名， 如果命名不规范就重明名
            curr_checked_shot.rename()

            dst_full_path = curr_checked_shot.get_dst_path()    # 在GYProject 的 路径

            """
            print 'current path is %s ' % curr_checked_shot.shot_name
            print dst_full_path
            print curr_checked_shot.check_shot_msg()
            """

            # 复制到对应的路径
            result = curr_checked_shot.copy_src_to_dst(curr_checked_shot.shot_name, dst_full_path)

            # 提交检查
            if result:
                curr_checked_shot.submit_to_cgtw(dst_full_path)
                print 'submit success'

        else:
            pass


if __name__ == "__main__":
    write_down_variable_ui()
    project_item = r"Z:\Temp\render\CGTW\Manually_Rename\project_item.json"
    proj_exps = reload_json_attr(project_item)
    proj = proj_exps["proj"]
    path = proj_exps["file_path"]
    stage = proj_exps["dept"]

    res_files_vector = get_files_abs_path(path)
    res_files = handle_backslash(res_files_vector)

    run_process(proj, stage, res_files)

#%% [markdown]
#  #### set up telegram notifications
#  не очень понятно, нужно ли это.
#
#  если нужно -- напишите @oserikov в телеграме, я расскажу, что сделать,
#  чтобы присылались сообщения с качеством модели когда она отработает.

#%%
telegram_notifications_enabled=False
EXP_DESCRIPTION = "PREDICT ONLY MORPHOLOGICAL ANALYSIS"

if telegram_notifications_enabled:
    bot_token = input("введите telegram bot token: ")
    chat_id = "292749902" # for @oserikov

#%% [markdown]
# #### install prereqs

#%%
get_ipython().system(f"git clone https://github.com/NIS-2018-CROSS-M/colab-tools.git")
get_ipython().magic(f"cd colab-tools")
get_ipython().system(f"bash colab-install-opennmt.sh")
get_ipython().system(f"bash colab-install-cuda92-pytorch41.sh")
get_ipython().system(f"bash colab-install-torchtext.sh")
get_ipython().magic(f"cd ..")


#%%
# install dependencies used in calma project
get_ipython().system('/usr/bin/python3 -m pip install configargparse')
get_ipython().system('git clone https://github.com/NIS-2018-CROSS-M/calma_tools.git')

# receive the calma
get_ipython().system('git clone https://github.com/ftyers/calma.git')
get_ipython().magic('cd calma')
get_ipython().system('git checkout -b latest-known-version d4ce3758d06538933855f734a44630efc8e2b6b2')
get_ipython().system('rm sharedtaskdata/onmt-data/*')
get_ipython().system('rm sharedtaskdata/results/*')
get_ipython().magic('cd ..')


#%%
from collections import defaultdict as dd
from random import shuffle
import re
import sys
sys.path.append(get_ipython().getoutput("readlink -e calma_tools")[0])
from calma_tools.ml_util import MLUtil
import urllib


#%%
get_ipython().magic('cd calma/sharedtaskdata')


#%%
langs=['crh']
tracks=['2']
data_classes = ['test', 'dev']

train_steps=1000
valid_steps=100
save_checkpoint_steps = valid_steps

train_params = [
    f"-train_steps {train_steps}",
    f"-valid_steps {valid_steps}",
    f"-save_checkpoint_steps {save_checkpoint_steps}",
    f"-world_size 1",
    f"-gpu_ranks 0 1",
    f"-encoder_type brnn"
]

pred_params = [
    f"-replace_unk",
    f"-verbose",
    f"-n_best 8",
    f"-beam 8"
]

#%% [markdown]
#  #### data modification


#%%
class TrainDataModifyer:
    @staticmethod
    def modify_src_line(line):
        return line


    @staticmethod
    def restore_src_line(line):
        return line


    @staticmethod
    def modify_tgt_line(line):
        return ' '.join(['+' + tag for tag in line.split('+') if '=' in tag and not tag.startswith("Language=")]).rstrip(' ')

    @staticmethod
    def restore_tgt_line(line):
        return line


class NBestDataModifyer:
    @staticmethod
    def sent_to_baseline_compatible(line):
        return line
      
    @staticmethod
    def hyp_to_baseline_compatible(line):
        line_splitted = line.split('] [')
        line_splitted[1] = line_splitted[1].rstrip(']')  # (line_splitted[1].split(']')[0])
        if len(line_splitted) < 2 or line_splitted[1] == "":
            line_splitted[1] = '\'+Tag0=?\''
        return line_splitted[0] + '] [' + ', '.join(['\'c\'', '\'c\'', '\'+NOUN\'', line_splitted[1], '\'+Language=lan\'']) + ']'


class DataEvaluator:
    otypes = ["analysis","lemma","tag"]
    
    @staticmethod
    def update_data(data, line):
        lan, wf, lemma, pos, msd = line.split('\t')

        data["morph analysis"][wf].add(msd)
        
        return data

#%% [markdown]
#  #### ml

#%%
class CognatesTool:
    words_info = {}

    def __init__(self, ud_data_filenames):
        for fn in ud_data_filenames:
            with open(fn, 'r', encoding="utf-8") as f:
                for line in f:
                    lang, wf, lemma, pos, morph_a = line.rstrip().split('\t')
                    if wf not in self.words_info.keys():
                        self.words_info[wf] = []
                    
                    self.words_info[wf].append(
                        {
                            "lang": lang,
                            "wf": wf,
                            "lemma": lemma,
                            "pos": pos,
                            "morph_a": morph_a
                        }
                    )
        print(str(len(self.words_info.keys())) + " words have cognates")

    def get_words(self):
        return self.words_info.keys()

    def word_has_cognates(self, word):
        return word in self.get_words()

    def has_cognates(self, line, onmt_style=False):
        if onmt_style:
            res = self.word_has_cognates(''.join(line.rstrip().split()))
        else:
            # ud style lang \t wordform \t lemma \t pos \t analyses \t i want to sleeeeep
            res = self.word_has_cognates(line.rstrip().split('\t')[1])
        return res

    def predict(self, src_filename, output_filename):
        with open(src_filename, 'r', encoding="utf-8") as f_src,             open(output_filename, 'w', encoding="utf-8") as f_tgt:
            
            for line in f_src:
                lang, wf, lemma, pos, morph_a = line.rstrip().split('\t')
                
                if wf not in self.get_words():
                    continue                
                
                for analysis_set in self.words_info[wf]:
                    print('\t'.join([analysis_set["lang"],
                                     analysis_set["wf"],
                                     analysis_set["lemma"],
                                     analysis_set["pos"],
                                     analysis_set["morph_a"]]),
                          file=f_tgt)


#%%
def ml(langs, tracks, train_params, prediction_params, dataModifyer, nbestModifyer, dataEvaluator):
    mlUtil = MLUtil(prediction_params, dataModifyer, nbestModifyer)
    for lang in langs:
        for track in tracks:

            # filenames, many of them
            train_covered_filename = f"train/{lang}-track{track}-covered"
            train_uncovered_filename = f"train/{lang}-track{track}-uncovered"
            train_res_src_filename = f"onmt-data/{lang}-track{track}-src-train.txt"
            train_res_tgt_filename = f"onmt-data/{lang}-track{track}-tgt-train.txt"

            test_covered_filename = f"test/{lang}-covered"
            test_uncovered_filename = f"test/{lang}-uncovered"
            test_res_src_filename = f"onmt-data/{lang}-track{track}-src-test.txt"
            test_res_tgt_filename = f"onmt-data/{lang}-track{track}-tgt-test.txt"
            test_pred_output_filename = f"results/{lang}-track{track}-test-covered.sys" # output :)

            val_covered_filename = f"dev/{lang}-covered"
            val_uncovered_filename = f"dev/{lang}-uncovered"
            val_res_src_filename = f"onmt-data/{lang}-track{track}-src-dev.txt"
            val_res_tgt_filename = f"onmt-data/{lang}-track{track}-tgt-dev.txt"
            val_pred_output_filename = f"results/{lang}-track{track}-dev-covered.sys" # output :)


            model_filename = f"models/{lang}-track{track}.model"

            score_log_filename = f"{lang}-{track}-score.log"
            get_ipython().system(f'touch {score_log_filename}')


            # ml| data preprocessing
            mlUtil.generate_data(train_uncovered_filename, train_res_src_filename, train_res_tgt_filename)
            mlUtil.generate_data(val_uncovered_filename, val_res_src_filename, val_res_tgt_filename)
            mlUtil.generate_data(test_covered_filename, test_res_src_filename, test_res_tgt_filename)

            # ml| training
            mlUtil.train(train_res_src_filename, train_res_tgt_filename, val_res_src_filename, val_res_tgt_filename, model_filename, train_params)

            # ml| predict and eval for test
            mlUtil.predict(model_filename, test_res_src_filename, test_covered_filename, test_pred_output_filename)
            get_ipython().system(f'echo "*===QUALITY ON TEST DATA===*" >> {score_log_filename}')
            mlUtil.score_predictions(test_pred_output_filename, test_uncovered_filename, score_log_filename, dataEvaluator)


            # ml| predict and eval for val
            mlUtil.predict(model_filename, val_res_src_filename, val_covered_filename, val_pred_output_filename)


            get_ipython().system(f'echo "*===QUALITY ON VAL DATA===*" >> {score_log_filename}')
            mlUtil.score_predictions(val_pred_output_filename, val_uncovered_filename, score_log_filename, dataEvaluator)

            # log eval results
            get_ipython().system(f'cat {score_log_filename}')

            # send eval to @oserikov at telegram
            if telegram_notifications_enabled:
                telegram_message = f"#score\n{lang}\n{track}\n"+''.join(open(score_log_filename).readlines())+'\n'+EXP_DESCRIPTION

                telegram_message_encoded = urllib.parse.quote(telegram_message)
                get_ipython().system(f'curl -i -X GET "https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={telegram_message_encoded}&parse_mode=markdown"')


#%%
ml(langs, tracks, train_params, pred_params, TrainDataModifyer, NBestDataModifyer, DataEvaluator)

#%% [markdown]
#  # sandbox

#%%




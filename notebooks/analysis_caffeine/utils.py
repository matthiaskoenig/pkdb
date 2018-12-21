import requests
import numpy as np
from collections import namedtuple
from urllib.parse import urljoin, urlencode
import pandas as pd
import attr
from pathlib import Path


# Styles for plots
ccolors = {'control': 'black',
           'smoking': 'blue',
           'oc': 'green',
           'outlier': 'red',
          }
markers = {'control': 's',
           'smoking': 'd',
           'oc': 'o',
            'outlier': 'x',

          }

def unstring(value):
    if isinstance(value,str):
        return eval(value)
    else:
        return value
    
def array_from_string(value):
    try:
        return np.array(unstring(value)).astype('float32')
    except SyntaxError:
        return np.fromstring(value.strip('[]') ,dtype=float, sep=" ")
    
    
        
        
    
category_filter = {
    'control':{
        ('smoking', 'choice'):"N",
        #('oral contraceptives', 'choice'):'N',
        #('medication', 'choice'):'N',
        (('oral contraceptives','choice'),('medication','choice')):('N','N'),

       'outlier':False
    },
    'smoking':{
        ('smoking', 'choice'):"Y",
        'outlier':False
    }, 
    'oc':{
        ('oral contraceptives', 'choice'):'Y',
        'outlier':False
    },
    'outlier':{
        'outlier':True
    }}


def convert_unit(df, unit_in, unit_out, factor=1.0, 
                 unit_field="unit", data_fields=['mean','median','value', 'sd', 'se', 'min', 'max'], inplace=True, subset=False):
    """ Unit conversion in given data frame. """
    if not inplace:
        df = df.copy()
    if subset:
        for column in subset:
            is_weightidx =  df[column].notnull() 
            df = df[is_weightidx]     
            if isinstance(factor, pd.Series):
                factor = factor[is_weightidx]
        
        
    idx = (df[unit_field] == unit_in)
    

    for key in data_fields:
        df.loc[idx, key] = df.loc[idx, key]*factor
    df.loc[idx, unit_field] = unit_out
    
    if subset:
        return df[idx]
    
    return df

def caffeine_idx(data):
    return (data.substance_name_intervention == 'caffeine') \
           & (data.substance_name == 'caffeine') \
           & (data[ ('healthy', 'choice')] == 'Y') \
           & (data['tissue'] == 'plasma')

def pktype_data(data,pktype):
    return data[data.pktype==pktype]
    

def abs_idx(data,unit_field):
    return ~rel_idx(data,unit_field)

def rel_idx(data,unit_field):
    return data[unit_field].str.contains('kg')

def filter_out(data,unit_field,units):
    return data[~data[unit_field].isin(units)]

def filter_df(filter_dict, df):
    for filter_key, filter_value in filter_dict.items():
        if isinstance(filter_value, tuple):
            temp_df = []
            for f_key, f_value in zip(filter_key,filter_value):
                temp_df.append(df[df[f_key]==f_value])
            df = pd.concat(temp_df)
        else:    
            df = df[df[filter_key]==filter_value]
    return df

def group_idx(data):
    return data["subject_type"] == 'group'

def individual_idx(data):
    return data["subject_type"] == 'individual'

def get_data(url,**kwargs):
    """
    gets the data from a paginated rest api. 
    """
    
    url_params = "?"+urlencode(kwargs)
    acctual_url = urljoin(url,url_params)
    response = requests.get(acctual_url)
    num_pages = response.json()["last_page"]
    data = []
    for page in range(1,num_pages +1):
        url_current = acctual_url + f"&page={page}"
        response = requests.get(url_current)
        data += response.json()["data"]["data"]

    flatten_data = [flatten_json(d) for d in data]
    return pd.DataFrame(flatten_data)

def flatten_json(y):
    """
    
    """
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        #elif type(x) is list:
        #    i = 0
        #    for a in x:
        #        flatten(a, name + str(i) + '_')
        #       i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

def my_tuple(data):
    
    if any(data):
        if len(data) == 1:
            return tuple(data)[0]
        return tuple(data)
    else:
        np.NaN


def add_level_to_df(df, level_name):
    df.columns = pd.MultiIndex.from_tuples(list(zip(df.columns, len(df.columns)*[level_name])))
    return  df.swaplevel(axis=1)     


@attr.s
class PkdbModel(object):
    
    name = attr.ib()
    base_url =  attr.ib(default="http://0.0.0.0:8000/api/v1/")
    loaded = attr.ib(default=False)
    preprocessed =  attr.ib(default=False)
    saved = attr.ib(default=False)
    destination =  attr.ib(default="0-raw")
    
    @property
    def path(self):
        return Path.cwd() / "data" / self.destination / f"{self.name}.tsv"

    @property
    def base_params(self):
        if self.name in ["individuals","groups"]:
                   return {"format":"json"} 
        else:
            return {"format":"json", "final":"true"}
    
    @property
    def url(self):
         return urljoin(self.base_url, f'{self.name}_elastic/')
        
    def add_data(self, data):
        self.data = data    
    
    def load(self):
        self.data = get_data(self.url, **self.base_params)
        self.loaded = True

    def preprocess(self):
        self.data.dropna(how="all",axis=1, inplace=True)
        self._preprocess_outputs()
        self._preprocess_interventions()
        self._preprocess_characteristica()
        self.preprocessed = True
        self.destination = "1-preprocessed"
    
    
    @property
    def read_kwargs(self): 
        if self.name in ["interventions"]:
             return {'header' :[0],'index_col': [0,1,2]}
        elif self.name in ["outputs", 'timecourses']:
             return {'header' :[0],'index_col': [0,1]}
        elif self.name in ["individuals", "groups"]:
             return {'header' :[0,1],'index_col': [0,1,2]}
        elif self.name in ["all_subjects"]:
            return {'header':[0,1], "index_col":[0,1,2,3]}
        elif self.name in ["all_complete","groups_complete","individuals_complete","caffeine_timecourse","caffeine_clearance"]:
            return {'header':[0], "index_col":[0]}
        elif self.name in ["all_results"]:
            return {'header':[0]}
    
    
        
    def save(self):
        self.data.to_csv(self.path, sep="\t")
        self.saved = True
    
    def read(self):
        self.data = pd.read_csv(self.path, sep="\t",**self.read_kwargs)
        self.data.columns = [eval(c) if "," in c else c for c in list(self.data.columns) ]
    
    def to_array(self):
        for value in ["mean","median","sd","se","cv","value","time"]:
            self.data[value] = self.data[value].apply(lambda x :array_from_string(x))
            
        
          

    def report(self):
        print("_"*60)
        print(f"Name: {self.name}")
        print(f"Loaded: {self.loaded}")
        print(f"Preprocessed: {self.preprocessed}")
        print(f"saved: {self.saved}")
        if all([self.loaded,self.preprocessed,self.saved]):
            print(f"{self.name} were succsesfully saved to <{self.path}>")
    
    @property
    def select_output(output):
        return 
        
        
    def _preprocess_outputs(self):
        if self.name in ["outputs","timecourses"]:
            self.data.drop(["final","individual_name","group_name"],axis=1, inplace=True)
            self.data["interventions"] = self.data["interventions"].apply(lambda interventions: interventions[0]['pk'] if len(interventions) == 1 else np.nan)
            self.data.dropna(subset = ["interventions"], inplace=True)
            self.data.interventions = self.data.interventions.astype(int)
            # sort columns by number of not nan values
            self.data = self.data[self.data.apply(lambda x: x.count()).sort_values(ascending=False).index]
            self.data.set_index(["study","pk"], inplace=True)
            
    def _preprocess_interventions(self):
        if self.name in ["interventions"]:
            self.data = self.data.drop("final",axis=1)
            self.data = self.data[self.data.apply(lambda x: x.count()).sort_values(ascending=False).index]
                               
            self.data.set_index(["study","pk","name"], inplace=True)
    
    def _preprocess_characteristica(self):
        if self.name in ["individuals", "groups"]:
            lst_col = 'characteristica_all_final'
            intermidiate_df = pd.DataFrame({col:np.repeat(self.data[col].values, self.data[lst_col].str.len()) for col in self.data.columns.difference([lst_col])}).assign(**{lst_col:np.concatenate(self.data[lst_col].values)})[self.data.columns.tolist()]
            df = intermidiate_df["characteristica_all_final"].apply(pd.Series)
            df["study"] = intermidiate_df["study_name"]
            df.drop(["pk", "ctype"], axis=1,inplace=True)
            df["subject_pk"] = intermidiate_df["pk"]
            df["subject_name"] = intermidiate_df["name"]

            df = df.pivot_table(index=["study","subject_pk","subject_name"], columns=["category"], aggfunc=my_tuple)
            df.columns = df.columns.swaplevel(0, 1)
            df = df[df.groupby(level=0, axis=0).count().sum().max(level=0).sort_values(ascending=False).index]
            df.dropna(how="all", axis=1, inplace=True)
            self.data = df

@attr.s
class Preprocessed(object):
    
    destination = attr.ib(default="2-merged")
    
    def read(self):
        for field in self._preprocessed_fields:
            pkdb_model = PkdbModel(name=field, destination="1-preprocessed")
            pkdb_model.read()
            setattr(self,field,pkdb_model)
    
    def merge(self):
        #self.interventions.data = add_level_to_df(self.interventions.data,"intervention")
        #self.timecourses.data = add_level_to_df(self.timecourses.data,"timecourse")
        #self.outputs.data = add_level_to_df(self.outputs.data,"output")

        self._merge_groups_individuals()
        self._merge_outputs_timecourses()
        self._merge_individuals_interventions_all_results()
        self._merge_groups_interventions_all_results()
        self._merge_all_subjects_interventions_all_results()

    def save(self):
        for field in self._merged_fields:
            getattr(self,field).save()
            
    
    @property
    def _preprocessed_fields(self):
        return ['outputs','timecourses','interventions','individuals','groups']
    
    @property
    def _merged_fields(self):
        return ["all_subjects", "all_results", "individuals_complete", "groups_complete","all_complete"]
    
    def _merge_groups_individuals(self):
        df = pd.concat([self.individuals.data,self.groups.data], keys=["individual","group"])   
        df.reset_index(inplace=True)
        df.rename(columns={"level_0":"subject_type"},inplace=True)
        df.set_index(["study","subject_type","subject_pk","subject_name"], inplace=True)
        df = df[df.groupby(level=0, axis=0).count().sum().max(level=0).sort_values(ascending=False).index]
        df = df.dropna(how="all", axis=1)
        all_subjects = PkdbModel(name="all_subjects", destination=self.destination)
        all_subjects.add_data(df)
        self.all_subjects = all_subjects
    
    def _merge_outputs_timecourses(self):
        df = pd.concat([self.outputs.data,self.timecourses.data], keys=["outputs","timecourses"])   
        df.reset_index(inplace=True)
        df.rename(columns={"level_0":"output_type"},inplace=True)
        df.set_index(["study","output_type","pk"], inplace=True)
        df = df[df.groupby(level=0, axis=0).count().sum().max(level=0).sort_values(ascending=False).index]
        df = df.dropna(how="all", axis=1)
        all_results = PkdbModel(name="all_results", destination=self.destination)
        all_results.add_data(df)
        self.all_results = all_results
    
    def _merge_individuals_interventions_all_results(self):
        #all_results = add_level_to_df(self.interventions.data,"intervention")
        #intervention = add_level_to_df(self.timeocourses.data,"timecourse")
        #self.outputs.data = add_level_to_df(self.interventions.data,"output")

        individuals_complete_intermediate = pd.merge(left=self.all_results.data, right=self.interventions.data,  how='inner', suffixes=('','_intervention'),left_on='interventions', right_on="pk")
        individuals_complete_df = pd.merge(individuals_complete_intermediate,self.individuals.data.reset_index(),  how='inner', suffixes=('','subject'),left_on='individual_pk', right_on="subject_pk")
        individuals_complete = PkdbModel(name="individuals_complete", destination=self.destination)
        individuals_complete.add_data(individuals_complete_df)
        self.individuals_complete = individuals_complete
    
    def _merge_groups_interventions_all_results(self):
        groups_complete_intermediate = pd.merge(left=self.all_results.data, right=self.interventions.data,  how='inner', suffixes=('','_intervention'),left_on='interventions', right_on="pk")
        groups_complete_df = pd.merge(groups_complete_intermediate,self.groups.data.reset_index(),  how='inner', suffixes=('','subject'),left_on='group_pk', right_on="subject_pk")
        groups_complete = PkdbModel(name="groups_complete", destination=self.destination)
        groups_complete.add_data(groups_complete_df)
        self.groups_complete = groups_complete
    
    def _merge_all_subjects_interventions_all_results(self):
        
        all_complete_intermediate = pd.merge(left=self.all_results.data.reset_index(), right=self.interventions.data,  how='left', suffixes=('','_intervention'),left_on='interventions', right_on="pk")
        
        all_complete_intermediate["subject_type"] = False
        all_complete_intermediate["subject_pk"] = False

        group_idx = all_complete_intermediate["group_pk"].notnull()
        individual_idx = all_complete_intermediate["individual_pk"].notnull()

        
        all_complete_intermediate.loc[group_idx,"subject_type"] = "group"
        all_complete_intermediate.loc[individual_idx,"subject_type"] = "individual"
        
        all_complete_intermediate.loc[group_idx,"subject_pk"] = all_complete_intermediate[group_idx]["group_pk"]
        all_complete_intermediate.loc[individual_idx,"subject_pk"] = all_complete_intermediate[individual_idx]["individual_pk"]
        all_complete_df = pd.merge(all_complete_intermediate,self.all_subjects.data.reset_index(),  how='inner', suffixes=('','subject'), on=["subject_pk","subject_type"] )
        all_complete = PkdbModel(name="all_complete", destination=self.destination)
        all_complete.add_data(all_complete_df)
        self.all_complete = all_complete
        
    def _add_per_bodyweight(self):
            return None
        
        
@attr.s
class Result(object):
    compelete_all = attr.ib()
    
    
    def plot(self):
        return None
        
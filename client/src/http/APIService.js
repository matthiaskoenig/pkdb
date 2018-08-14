import axios from 'axios';
const API_URL = 'http://localhost:8000';
export class APIService{
    constructor(){
}

    getReferences() {
      const url = `${API_URL}/api/v1/references/`;
      return axios.get(url).then(response => response.data);
    }

    getReference(pk) {
          const url = `${API_URL}/api/v1/references/${pk}`;
          return axios.get(url).then(response => response.data);
      }

    updateReference(pk){
        const url = `${API_URL}/api/preferences/${pk}`;
        return axios.put(url,pk);
    }
}


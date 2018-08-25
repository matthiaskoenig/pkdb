<template>
    <div>
        <h1>References <span v-if="count">({{ count }})</span></h1>
        <table v-if="count">
            <thead>
            <tr>
                <th>sid</th>
                <th>pmid</th>
                <th>name</th>
                <th>title</th>
                <th>journal</th>
                <th>date</th>
                <th>abstract</th>
            </tr>
            </thead>
            <tbody>
            <tr v-for="(reference, index) in results" :key="index">
                <td>{{ reference.sid }}</td>
                <td>{{ reference.pmid }}</td>
                <td>{{ reference.name }}</td>
                <td>{{ reference.title }}</td>
                <td>{{ reference.journal }}</td>
                <td>{{ reference.date }}</td>
                <td>{{ reference.abstract }}</td>
            </tr>
            </tbody>
        </table>
        <p>
        </p>
    </div>
</template>

<script>
import axios from 'axios';
export default {
    name: 'References',
    props: {
        api: String
    },
    methods:{
        get: function(){
            var api_url
            api_url = this.api + '/references/?format=json'


            axios.get(api_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.data = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })
        }
    },
    data() {
        return {
            data: {
                'count': null,
                'next': null,
                'previous': null,
                'results': null,
            },
            errors: []
        }
    },
    computed: {
        count: function () {
            return this.data['count']
        },
        next: function () {
            return this.data['next']
        },
        previous: function () {
            return this.data['previous']
        },
        results: function () {
            return this.data['results']
        },
    },
    created: function() {
        this.get()
    }
}
</script>
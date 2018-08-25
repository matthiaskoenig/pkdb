<template>
    <div>
        <h1>References ({{count}})</h1>
        <table>
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
    mounted() {
        axios.get(`http://localhost:8000/api/v1/references/?format=json`)
            .then(response => {
                // JSON responses are automatically parsed.
                this.data = response.data
            })
            .catch(e => {
                this.errors.push(e)
            })

        // async / await version (created() becomes async created())
        //
        // try {
        //   const response = await axios.get(`http://jsonplaceholder.typicode.com/posts`)
        //   this.posts = response.data
        // } catch (e) {
        //   this.errors.push(e)
        // }

    }
}
</script>
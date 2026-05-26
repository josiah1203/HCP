import { HttpClient } from "./http.js";
import { BomResource } from "./resources/bom.js";
import { GraphResource } from "./resources/graph.js";
import { ObjectsResource } from "./resources/objects.js";
import { ProjectsResource } from "./resources/projects.js";
import { SearchResource } from "./resources/search.js";
import type { ClientOptions } from "./types.js";

export class Client {
  readonly projects: ProjectsResource;
  readonly objects: ObjectsResource;
  readonly bom: BomResource;
  readonly graph: GraphResource;
  readonly search: SearchResource;

  private readonly http: HttpClient;

  constructor(options: ClientOptions = {}) {
    this.http = new HttpClient(options);
    this.projects = new ProjectsResource(this.http);
    this.objects = new ObjectsResource(this.http);
    this.bom = new BomResource(this.http);
    this.graph = new GraphResource(this.http);
    this.search = new SearchResource(this.http);
  }
}
